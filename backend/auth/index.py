"""
Auth функция: регистрация, вход, верификация email-кода, 2FA.
Действия: send_code, verify_code, register, login, verify_2fa, get_me, update_profile, logout
"""
import json
import os
import random
import string
import hashlib
import smtplib
import secrets
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import psycopg2

SCHEMA = os.environ.get('MAIN_DB_SCHEMA', 'public')
CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-User-Id, X-Auth-Token, X-Session-Id, X-Authorization',
}


def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def generate_code() -> str:
    return ''.join(random.choices(string.digits, k=6))


def generate_token() -> str:
    return secrets.token_hex(32)


def send_email(to_email: str, subject: str, html_body: str):
    gmail_user = os.environ['GMAIL_USER']
    gmail_pass = os.environ['GMAIL_PASSWORD']
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f'OxiwisAI <{gmail_user}>'
    msg['To'] = to_email
    msg.attach(MIMEText(html_body, 'html'))
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, to_email, msg.as_string())


def code_email_html(code: str, purpose: str) -> str:
    purpose_text = 'входа' if purpose == 'login' else 'регистрации'
    return f"""
    <div style="background:#0a0a0a;padding:40px;font-family:'Helvetica Neue',Arial,sans-serif;color:#fff;max-width:520px;margin:0 auto;border-radius:16px;border:1px solid rgba(255,255,255,0.08)">
      <div style="text-align:center;margin-bottom:32px">
        <span style="font-size:28px;font-weight:300;letter-spacing:2px;color:#fff">OxiwisAI</span>
        <div style="font-size:11px;color:#666;letter-spacing:3px;text-transform:uppercase;margin-top:4px">by Oxiwis</div>
      </div>
      <p style="color:#aaa;font-size:14px;margin-bottom:24px;line-height:1.6">Ваш код для {purpose_text}:</p>
      <div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:28px;text-align:center;letter-spacing:12px;font-size:36px;font-weight:700;color:#fff;margin-bottom:24px">
        {code}
      </div>
      <p style="color:#555;font-size:12px;text-align:center">Код действителен 10 минут. Не передавайте его никому.</p>
    </div>
    """


def handler(event: dict, context) -> dict:
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS, 'body': ''}

    body = json.loads(event.get('body') or '{}')
    action = body.get('action', '')
    conn = get_conn()
    cur = conn.cursor()

    try:
        # --- SEND CODE ---
        if action == 'send_code':
            email = body.get('email', '').strip().lower()
            purpose = body.get('purpose', 'login')
            if not email or '@' not in email:
                return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Неверный email'})}

            code = generate_code()
            expires = datetime.utcnow() + timedelta(minutes=10)

            cur.execute(
                f"UPDATE {SCHEMA}.email_codes SET used=true WHERE email=%s AND used=false",
                (email,)
            )
            cur.execute(
                f"INSERT INTO {SCHEMA}.email_codes (email, code, purpose, expires_at) VALUES (%s, %s, %s, %s)",
                (email, code, purpose, expires)
            )
            conn.commit()

            send_email(email, f'Ваш код OxiwisAI: {code}', code_email_html(code, purpose))
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'ok': True, 'message': 'Код отправлен'})}

        # --- VERIFY CODE (check only) ---
        elif action == 'verify_code':
            email = body.get('email', '').strip().lower()
            code = body.get('code', '').strip()

            cur.execute(
                f"SELECT id FROM {SCHEMA}.email_codes WHERE email=%s AND code=%s AND used=false AND expires_at > NOW() ORDER BY created_at DESC LIMIT 1",
                (email, code)
            )
            row = cur.fetchone()
            if not row:
                return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Неверный или истёкший код'})}

            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'ok': True, 'valid': True})}

        # --- REGISTER ---
        elif action == 'register':
            email = body.get('email', '').strip().lower()
            code = body.get('code', '').strip()
            name = body.get('name', '').strip()
            password = body.get('password', '')
            enable_2fa = body.get('enable_2fa', False)

            cur.execute(
                f"SELECT id FROM {SCHEMA}.email_codes WHERE email=%s AND code=%s AND used=false AND expires_at > NOW() ORDER BY created_at DESC LIMIT 1",
                (email, code)
            )
            code_row = cur.fetchone()
            if not code_row:
                return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Неверный или истёкший код'})}

            cur.execute(f"SELECT id FROM {SCHEMA}.users WHERE email=%s", (email,))
            if cur.fetchone():
                return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Email уже зарегистрирован'})}

            pw_hash = hash_password(password) if password else None
            cur.execute(
                f"INSERT INTO {SCHEMA}.users (email, name, password_hash, has_2fa) VALUES (%s, %s, %s, %s) RETURNING id",
                (email, name or email.split('@')[0], pw_hash, enable_2fa and bool(password))
            )
            user_id = cur.fetchone()[0]

            cur.execute(f"UPDATE {SCHEMA}.email_codes SET used=true WHERE id=%s", (code_row[0],))

            token = generate_token()
            expires = datetime.utcnow() + timedelta(days=30)
            cur.execute(
                f"INSERT INTO {SCHEMA}.sessions (user_id, token, expires_at) VALUES (%s, %s, %s)",
                (str(user_id), token, expires)
            )
            conn.commit()

            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({
                'ok': True, 'token': token, 'user': {
                    'id': str(user_id), 'email': email, 'name': name or email.split('@')[0], 'has_2fa': enable_2fa and bool(password)
                }
            })}

        # --- LOGIN ---
        elif action == 'login':
            email = body.get('email', '').strip().lower()
            code = body.get('code', '').strip()
            password = body.get('password', '')

            cur.execute(
                f"SELECT id FROM {SCHEMA}.email_codes WHERE email=%s AND code=%s AND used=false AND expires_at > NOW() ORDER BY created_at DESC LIMIT 1",
                (email, code)
            )
            code_row = cur.fetchone()
            if not code_row:
                return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Неверный или истёкший код'})}

            cur.execute(f"SELECT id, name, password_hash, has_2fa FROM {SCHEMA}.users WHERE email=%s", (email,))
            user = cur.fetchone()
            if not user:
                return {'statusCode': 404, 'headers': CORS, 'body': json.dumps({'error': 'Пользователь не найден'})}

            user_id, name, pw_hash, has_2fa = user

            if has_2fa and pw_hash:
                if not password:
                    return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'ok': True, 'require_2fa': True, 'email': email, 'code': code})}
                if hash_password(password) != pw_hash:
                    return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Неверный пароль'})}

            cur.execute(f"UPDATE {SCHEMA}.email_codes SET used=true WHERE id=%s", (code_row[0],))

            token = generate_token()
            expires = datetime.utcnow() + timedelta(days=30)
            cur.execute(
                f"INSERT INTO {SCHEMA}.sessions (user_id, token, expires_at) VALUES (%s, %s, %s)",
                (str(user_id), token, expires)
            )
            conn.commit()

            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({
                'ok': True, 'token': token, 'user': {'id': str(user_id), 'email': email, 'name': name, 'has_2fa': has_2fa}
            })}

        # --- GET ME ---
        elif action == 'get_me':
            token = (event.get('headers') or {}).get('x-authorization', '').replace('Bearer ', '')
            if not token:
                return {'statusCode': 401, 'headers': CORS, 'body': json.dumps({'error': 'Не авторизован'})}

            cur.execute(
                f"SELECT u.id, u.email, u.name, u.has_2fa, u.created_at FROM {SCHEMA}.sessions s JOIN {SCHEMA}.users u ON s.user_id=u.id WHERE s.token=%s AND s.expires_at > NOW()",
                (token,)
            )
            row = cur.fetchone()
            if not row:
                return {'statusCode': 401, 'headers': CORS, 'body': json.dumps({'error': 'Сессия недействительна'})}

            uid, email, name, has_2fa, created_at = row
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({
                'ok': True, 'user': {'id': str(uid), 'email': email, 'name': name, 'has_2fa': has_2fa, 'created_at': str(created_at)}
            })}

        # --- UPDATE PROFILE ---
        elif action == 'update_profile':
            token = (event.get('headers') or {}).get('x-authorization', '').replace('Bearer ', '')
            cur.execute(
                f"SELECT u.id FROM {SCHEMA}.sessions s JOIN {SCHEMA}.users u ON s.user_id=u.id WHERE s.token=%s AND s.expires_at > NOW()",
                (token,)
            )
            row = cur.fetchone()
            if not row:
                return {'statusCode': 401, 'headers': CORS, 'body': json.dumps({'error': 'Не авторизован'})}

            user_id = row[0]
            name = body.get('name')
            password = body.get('password')
            enable_2fa = body.get('enable_2fa')

            if name is not None:
                cur.execute(f"UPDATE {SCHEMA}.users SET name=%s, updated_at=NOW() WHERE id=%s", (name, str(user_id)))
            if password is not None:
                pw_hash = hash_password(password) if password else None
                cur.execute(f"UPDATE {SCHEMA}.users SET password_hash=%s, updated_at=NOW() WHERE id=%s", (pw_hash, str(user_id)))
            if enable_2fa is not None:
                cur.execute(f"UPDATE {SCHEMA}.users SET has_2fa=%s, updated_at=NOW() WHERE id=%s", (enable_2fa, str(user_id)))

            conn.commit()
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'ok': True})}

        # --- LOGOUT ---
        elif action == 'logout':
            token = (event.get('headers') or {}).get('x-authorization', '').replace('Bearer ', '')
            cur.execute(f"DELETE FROM {SCHEMA}.sessions WHERE token=%s", (token,))
            conn.commit()
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'ok': True})}

        return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Неизвестное действие'})}

    finally:
        cur.close()
        conn.close()
