"""
Аутентификация пользователей OxiwisAI: регистрация, вход, верификация кода, сессии.
"""
import json
import os
import random
import string
import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import psycopg2

SCHEMA = os.environ.get('MAIN_DB_SCHEMA', 't_p59434780_ai_site_development_')
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-User-Id, X-Auth-Token, X-Session-Id',
    'Access-Control-Max-Age': '86400',
}


def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split(':')
    if len(parts) != 2:
        return False
    salt, h = parts
    return hashlib.sha256((salt + password).encode()).hexdigest() == h


def generate_code() -> str:
    return ''.join(random.choices(string.digits, k=6))


def send_email(to_email: str, subject: str, html_body: str):
    gmail_user = os.environ.get('GMAIL_USER', '')
    gmail_pass = os.environ.get('GMAIL_PASSWORD', '')
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"OxiwisAI <{gmail_user}>"
    msg['To'] = to_email
    msg.attach(MIMEText(html_body, 'html'))
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, to_email, msg.as_string())


def send_code_email(to_email: str, code: str, purpose: str):
    if purpose == 'register':
        subject = 'Код подтверждения регистрации — OxiwisAI'
        action = 'подтверждения регистрации'
    elif purpose == 'login':
        subject = 'Код для входа — OxiwisAI'
        action = 'входа в аккаунт'
    elif purpose == '2fa':
        subject = 'Код двухфакторной аутентификации — OxiwisAI'
        action = 'двухфакторной аутентификации'
    else:
        subject = 'Код подтверждения — OxiwisAI'
        action = 'подтверждения'

    html = f"""
    <div style="background:#000;color:#fff;font-family:sans-serif;padding:40px;max-width:480px;margin:auto;border-radius:16px;">
      <div style="text-align:center;margin-bottom:32px;">
        <img src="https://cdn.poehali.dev/projects/bc51261c-a863-4d06-a23f-71157a55b74b/bucket/7e5e7698-9fd5-4062-aea0-5c3605825c09.jpg"
             width="64" style="border-radius:12px;" />
        <h2 style="margin:16px 0 4px;font-size:22px;font-weight:700;letter-spacing:2px;">OxiwisAI</h2>
        <p style="color:#888;font-size:13px;margin:0;">by Oxiwis</p>
      </div>
      <p style="color:#ccc;margin-bottom:24px;">Ваш код для {action}:</p>
      <div style="background:#111;border:1px solid #333;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px;">
        <span style="font-size:40px;font-weight:700;letter-spacing:12px;color:#fff;">{code}</span>
      </div>
      <p style="color:#666;font-size:13px;">Код действителен 10 минут. Не передавайте его никому.</p>
    </div>
    """
    send_email(to_email, subject, html)


def handler(event: dict, context) -> dict:
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    body = {}
    if event.get('body'):
        body = json.loads(event['body'])

    conn = get_conn()
    cur = conn.cursor()

    try:
        # POST /send-code — отправить код на email
        if method == 'POST' and '/send-code' in path:
            email = body.get('email', '').strip().lower()
            purpose = body.get('purpose', 'register')

            if not email:
                return {'statusCode': 400, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Email обязателен'})}

            if purpose == 'login':
                cur.execute(f"SELECT id FROM {SCHEMA}.users WHERE email = %s", (email,))
                if not cur.fetchone():
                    return {'statusCode': 404, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Пользователь не найден'})}

            code = generate_code()
            expires_at = datetime.utcnow() + timedelta(minutes=10)

            cur.execute(
                f"INSERT INTO {SCHEMA}.email_codes (email, code, purpose, expires_at) VALUES (%s, %s, %s, %s)",
                (email, code, purpose, expires_at)
            )
            conn.commit()

            send_code_email(email, code, purpose)
            return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'ok': True})}

        # POST /verify-code — проверить код
        elif method == 'POST' and '/verify-code' in path:
            email = body.get('email', '').strip().lower()
            code = body.get('code', '').strip()
            purpose = body.get('purpose', 'register')

            cur.execute(
                f"SELECT id FROM {SCHEMA}.email_codes WHERE email=%s AND code=%s AND purpose=%s AND used=FALSE AND expires_at > NOW() ORDER BY created_at DESC LIMIT 1",
                (email, code, purpose)
            )
            row = cur.fetchone()
            if not row:
                return {'statusCode': 400, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Неверный или просроченный код'})}

            cur.execute(f"UPDATE {SCHEMA}.email_codes SET used=TRUE WHERE id=%s", (row[0],))
            conn.commit()
            return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'ok': True})}

        # POST /register — регистрация
        elif method == 'POST' and '/register' in path:
            email = body.get('email', '').strip().lower()
            name = body.get('name', '').strip()
            password = body.get('password', '')
            has_2fa = body.get('has_2fa', False)

            if not email or not name:
                return {'statusCode': 400, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Email и имя обязательны'})}

            cur.execute(f"SELECT id FROM {SCHEMA}.users WHERE email=%s", (email,))
            if cur.fetchone():
                return {'statusCode': 409, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Пользователь уже существует'})}

            password_hash = hash_password(password) if password else None

            cur.execute(
                f"INSERT INTO {SCHEMA}.users (email, name, password_hash, has_2fa) VALUES (%s, %s, %s, %s) RETURNING id",
                (email, name, password_hash, has_2fa)
            )
            user_id = cur.fetchone()[0]

            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(days=30)
            cur.execute(
                f"INSERT INTO {SCHEMA}.sessions (user_id, token, expires_at) VALUES (%s, %s, %s)",
                (str(user_id), token, expires_at)
            )
            conn.commit()

            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({'token': token, 'user': {'id': str(user_id), 'email': email, 'name': name, 'has_2fa': has_2fa}})
            }

        # POST /login — вход
        elif method == 'POST' and '/login' in path:
            email = body.get('email', '').strip().lower()
            password = body.get('password', '')

            cur.execute(f"SELECT id, name, password_hash, has_2fa FROM {SCHEMA}.users WHERE email=%s", (email,))
            row = cur.fetchone()
            if not row:
                return {'statusCode': 404, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Пользователь не найден'})}

            user_id, name, password_hash, has_2fa = row

            if password_hash and not verify_password(password, password_hash):
                return {'statusCode': 401, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Неверный пароль'})}

            if has_2fa:
                return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'requires_2fa': True, 'email': email})}

            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(days=30)
            cur.execute(
                f"INSERT INTO {SCHEMA}.sessions (user_id, token, expires_at) VALUES (%s, %s, %s)",
                (str(user_id), token, expires_at)
            )
            conn.commit()

            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({'token': token, 'user': {'id': str(user_id), 'email': email, 'name': name, 'has_2fa': has_2fa}})
            }

        # POST /login-2fa — вход с 2FA (код на почту)
        elif method == 'POST' and '/login-2fa' in path:
            email = body.get('email', '').strip().lower()

            cur.execute(f"SELECT id, name, has_2fa FROM {SCHEMA}.users WHERE email=%s", (email,))
            row = cur.fetchone()
            if not row:
                return {'statusCode': 404, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Пользователь не найден'})}

            user_id, name, has_2fa = row
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(days=30)
            cur.execute(
                f"INSERT INTO {SCHEMA}.sessions (user_id, token, expires_at) VALUES (%s, %s, %s)",
                (str(user_id), token, expires_at)
            )
            conn.commit()

            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({'token': token, 'user': {'id': str(user_id), 'email': email, 'name': name, 'has_2fa': has_2fa}})
            }

        # GET /me — получить текущего пользователя
        elif method == 'GET' and '/me' in path:
            token = event.get('headers', {}).get('X-Auth-Token', '')
            if not token:
                return {'statusCode': 401, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Токен не передан'})}

            cur.execute(
                f"SELECT u.id, u.email, u.name, u.has_2fa FROM {SCHEMA}.sessions s JOIN {SCHEMA}.users u ON s.user_id=u.id WHERE s.token=%s AND s.expires_at > NOW()",
                (token,)
            )
            row = cur.fetchone()
            if not row:
                return {'statusCode': 401, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Сессия истекла'})}

            user_id, email, name, has_2fa = row
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({'user': {'id': str(user_id), 'email': email, 'name': name, 'has_2fa': has_2fa}})
            }

        # PUT /update-2fa — обновить 2FA настройки
        elif method == 'PUT' and '/update-2fa' in path:
            token = event.get('headers', {}).get('X-Auth-Token', '')
            has_2fa = body.get('has_2fa', False)

            cur.execute(
                f"SELECT u.id FROM {SCHEMA}.sessions s JOIN {SCHEMA}.users u ON s.user_id=u.id WHERE s.token=%s AND s.expires_at > NOW()",
                (token,)
            )
            row = cur.fetchone()
            if not row:
                return {'statusCode': 401, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Не авторизован'})}

            cur.execute(f"UPDATE {SCHEMA}.users SET has_2fa=%s, updated_at=NOW() WHERE id=%s", (has_2fa, row[0]))
            conn.commit()
            return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'ok': True})}

        # PUT /update-profile — обновить профиль
        elif method == 'PUT' and '/update-profile' in path:
            token = event.get('headers', {}).get('X-Auth-Token', '')
            name = body.get('name', '').strip()
            password = body.get('password', '')

            cur.execute(
                f"SELECT u.id FROM {SCHEMA}.sessions s JOIN {SCHEMA}.users u ON s.user_id=u.id WHERE s.token=%s AND s.expires_at > NOW()",
                (token,)
            )
            row = cur.fetchone()
            if not row:
                return {'statusCode': 401, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Не авторизован'})}

            user_id = row[0]
            if name:
                cur.execute(f"UPDATE {SCHEMA}.users SET name=%s, updated_at=NOW() WHERE id=%s", (name, user_id))
            if password:
                cur.execute(f"UPDATE {SCHEMA}.users SET password_hash=%s, updated_at=NOW() WHERE id=%s", (hash_password(password), user_id))
            conn.commit()
            return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'ok': True})}

        # POST /logout
        elif method == 'POST' and '/logout' in path:
            token = event.get('headers', {}).get('X-Auth-Token', '')
            cur.execute(f"UPDATE {SCHEMA}.sessions SET expires_at=NOW() WHERE token=%s", (token,))
            conn.commit()
            return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'ok': True})}

        if method == 'GET':
            return {'statusCode': 401, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Не авторизован'})}
        return {'statusCode': 404, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Not found'})}

    finally:
        cur.close()
        conn.close()