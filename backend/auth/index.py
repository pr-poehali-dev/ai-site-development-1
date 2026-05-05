"""
Auth: вход по email + код подтверждения. Авто-регистрация при первом входе.
Действия: send_code, login, get_me, update_name, logout
"""
import json
import os
import random
import string
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


def code_email_html(code: str) -> str:
    return f"""
    <div style="background:#0a0a0a;padding:48px 40px;font-family:'Helvetica Neue',Arial,sans-serif;color:#fff;max-width:520px;margin:0 auto;border-radius:20px;border:1px solid rgba(255,255,255,0.08)">
      <div style="text-align:center;margin-bottom:36px">
        <div style="display:inline-block;width:56px;height:56px;border:1px solid rgba(255,255,255,0.15);border-radius:14px;line-height:56px;font-size:22px;font-weight:300;letter-spacing:1px;margin-bottom:16px">O</div>
        <div style="font-size:24px;font-weight:300;letter-spacing:3px;color:#fff">OxiwisAI</div>
        <div style="font-size:10px;color:#555;letter-spacing:4px;text-transform:uppercase;margin-top:4px">by Oxiwis</div>
      </div>
      <p style="color:#888;font-size:14px;margin-bottom:28px;line-height:1.7;text-align:center">Your sign-in code / Ваш код для входа:</p>
      <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:14px;padding:32px;text-align:center;letter-spacing:14px;font-size:38px;font-weight:700;color:#fff;margin-bottom:28px;font-family:monospace">
        {code}
      </div>
      <p style="color:#444;font-size:12px;text-align:center;line-height:1.8">
        Valid for 10 minutes · Действителен 10 минут<br/>
        <span style="color:#333">Do not share this code with anyone</span>
      </p>
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
            if not email or '@' not in email:
                return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Invalid email'})}

            code = generate_code()
            expires = datetime.utcnow() + timedelta(minutes=10)

            cur.execute(
                f"UPDATE {SCHEMA}.email_codes SET used=true WHERE email=%s AND used=false",
                (email,)
            )
            cur.execute(
                f"INSERT INTO {SCHEMA}.email_codes (email, code, purpose, expires_at) VALUES (%s, %s, %s, %s)",
                (email, code, 'login', expires)
            )
            conn.commit()

            send_email(email, f'OxiwisAI — {code}', code_email_html(code))
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'ok': True})}

        # --- LOGIN (auto-register if new user) ---
        elif action == 'login':
            email = body.get('email', '').strip().lower()
            code = body.get('code', '').strip()

            cur.execute(
                f"SELECT id FROM {SCHEMA}.email_codes WHERE email=%s AND code=%s AND used=false AND expires_at > NOW() ORDER BY created_at DESC LIMIT 1",
                (email, code)
            )
            code_row = cur.fetchone()
            if not code_row:
                return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Invalid or expired code'})}

            cur.execute(f"SELECT id, name FROM {SCHEMA}.users WHERE email=%s", (email,))
            user_row = cur.fetchone()

            if user_row:
                user_id, name = user_row
            else:
                name = email.split('@')[0]
                cur.execute(
                    f"INSERT INTO {SCHEMA}.users (email, name) VALUES (%s, %s) RETURNING id",
                    (email, name)
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
                'ok': True, 'token': token,
                'user': {'id': str(user_id), 'email': email, 'name': name}
            })}

        # --- GET ME ---
        elif action == 'get_me':
            token = (event.get('headers') or {}).get('x-authorization', '').replace('Bearer ', '')
            cur.execute(
                f"SELECT u.id, u.email, u.name, u.created_at FROM {SCHEMA}.sessions s JOIN {SCHEMA}.users u ON s.user_id=u.id WHERE s.token=%s AND s.expires_at > NOW()",
                (token,)
            )
            row = cur.fetchone()
            if not row:
                return {'statusCode': 401, 'headers': CORS, 'body': json.dumps({'error': 'Unauthorized'})}

            uid, email, name, created_at = row
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({
                'ok': True, 'user': {'id': str(uid), 'email': email, 'name': name, 'created_at': str(created_at)}
            })}

        # --- UPDATE NAME ---
        elif action == 'update_name':
            token = (event.get('headers') or {}).get('x-authorization', '').replace('Bearer ', '')
            name = body.get('name', '').strip()
            cur.execute(
                f"SELECT u.id FROM {SCHEMA}.sessions s JOIN {SCHEMA}.users u ON s.user_id=u.id WHERE s.token=%s AND s.expires_at > NOW()",
                (token,)
            )
            row = cur.fetchone()
            if not row:
                return {'statusCode': 401, 'headers': CORS, 'body': json.dumps({'error': 'Unauthorized'})}
            if name:
                cur.execute(f"UPDATE {SCHEMA}.users SET name=%s, updated_at=NOW() WHERE id=%s", (name, str(row[0])))
                conn.commit()
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'ok': True})}

        # --- LOGOUT ---
        elif action == 'logout':
            token = (event.get('headers') or {}).get('x-authorization', '').replace('Bearer ', '')
            cur.execute(f"DELETE FROM {SCHEMA}.sessions WHERE token=%s", (token,))
            conn.commit()
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'ok': True})}

        if event.get('httpMethod') == 'GET':
            return {'statusCode': 401, 'headers': CORS, 'body': json.dumps({'error': 'Unauthorized'})}

        return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Unknown action'})}

    finally:
        cur.close()
        conn.close()
