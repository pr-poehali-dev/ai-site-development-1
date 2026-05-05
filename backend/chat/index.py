"""
Chat: отправка сообщений OxiwisAI, история чатов, лимит 256 запросов/сутки по МСК.
Поддерживает режим рассуждения (thinking mode).
"""
import json
import os
import urllib.request
import psycopg2
from datetime import datetime, timezone, timedelta

SCHEMA = os.environ.get('MAIN_DB_SCHEMA', 'public')
CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-User-Id, X-Auth-Token, X-Session-Id, X-Authorization',
}

OXIWIS_API_URL = 'https://jpdwcpxlotztzrqcgfeg.supabase.co/functions/v1/v1-chat'
OXIWIS_API_KEY = 'ypr_OBqnJxMDLkBWn3IztUOX6dcuW8hH3AfeUHrOAku7X3k'
DAILY_LIMIT = 256
MSK = timezone(timedelta(hours=3))


def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def get_user_from_token(cur, token: str):
    cur.execute(
        f"SELECT u.id, u.email, u.name FROM {SCHEMA}.sessions s JOIN {SCHEMA}.users u ON s.user_id=u.id WHERE s.token=%s AND s.expires_at > NOW()",
        (token,)
    )
    return cur.fetchone()


def get_msk_day() -> str:
    return datetime.now(MSK).strftime('%Y-%m-%d')


def check_and_increment_limit(cur, conn, user_id: str) -> tuple[bool, int]:
    today = get_msk_day()
    cur.execute(
        f"SELECT requests_count FROM {SCHEMA}.daily_limits WHERE user_id=%s AND day=%s",
        (user_id, today)
    )
    row = cur.fetchone()
    count = row[0] if row else 0

    if count >= DAILY_LIMIT:
        return False, count

    if row:
        cur.execute(
            f"UPDATE {SCHEMA}.daily_limits SET requests_count=requests_count+1 WHERE user_id=%s AND day=%s",
            (user_id, today)
        )
    else:
        cur.execute(
            f"INSERT INTO {SCHEMA}.daily_limits (user_id, day, requests_count) VALUES (%s, %s, 1)",
            (user_id, today)
        )
    conn.commit()
    return True, count + 1


def get_limit_info(cur, user_id: str) -> dict:
    today = get_msk_day()
    cur.execute(
        f"SELECT requests_count FROM {SCHEMA}.daily_limits WHERE user_id=%s AND day=%s",
        (user_id, today)
    )
    row = cur.fetchone()
    used = row[0] if row else 0
    return {'used': used, 'limit': DAILY_LIMIT, 'remaining': max(0, DAILY_LIMIT - used)}


def call_oxiwis(messages: list, thinking_mode: bool = False) -> str:
    payload_data = {
        'model': 'OxiwisAI',
        'messages': messages,
        'stream': False,
    }
    if thinking_mode:
        payload_data['thinking'] = True

    payload = json.dumps(payload_data).encode('utf-8')
    req = urllib.request.Request(
        OXIWIS_API_URL,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {OXIWIS_API_KEY}',
        },
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    if 'choices' in data and data['choices']:
        choice = data['choices'][0]
        msg = choice.get('message', {})
        thinking = msg.get('thinking', '')
        content = msg.get('content', '')
        if thinking and thinking_mode:
            return json.dumps({'thinking': thinking, 'content': content})
        return content
    if 'message' in data:
        msg = data['message']
        if isinstance(msg, dict):
            return msg.get('content', str(data))
        return str(msg)
    return str(data)


def handler(event: dict, context) -> dict:
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS, 'body': ''}

    token = (event.get('headers') or {}).get('x-authorization', '').replace('Bearer ', '')
    body = json.loads(event.get('body') or '{}')
    action = body.get('action', '')

    conn = get_conn()
    cur = conn.cursor()

    try:
        user = get_user_from_token(cur, token) if token else None
        if not user:
            return {'statusCode': 401, 'headers': CORS, 'body': json.dumps({'error': 'Unauthorized'})}

        user_id = str(user[0])

        # --- SEND MESSAGE ---
        if action == 'send_message':
            chat_id = body.get('chat_id')
            user_message = body.get('message', '').strip()
            thinking_mode = bool(body.get('thinking_mode', False))

            if not user_message:
                return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Empty message'})}

            allowed, count = check_and_increment_limit(cur, conn, user_id)
            if not allowed:
                return {'statusCode': 429, 'headers': CORS, 'body': json.dumps({
                    'error': 'Daily limit reached',
                    'limit': DAILY_LIMIT,
                    'used': count
                })}

            if chat_id:
                cur.execute(
                    f"SELECT id, messages, title FROM {SCHEMA}.chat_history WHERE id=%s AND user_id=%s",
                    (chat_id, user_id)
                )
                chat_row = cur.fetchone()
                if not chat_row:
                    return {'statusCode': 404, 'headers': CORS, 'body': json.dumps({'error': 'Chat not found'})}
                db_chat_id, existing_messages, title = chat_row
                messages = existing_messages if isinstance(existing_messages, list) else []
            else:
                messages = []
                title = user_message[:60]
                db_chat_id = None

            messages.append({'role': 'user', 'content': user_message})
            raw_reply = call_oxiwis(messages, thinking_mode)

            thinking_text = None
            reply_text = raw_reply

            if thinking_mode and raw_reply.startswith('{'):
                try:
                    parsed = json.loads(raw_reply)
                    thinking_text = parsed.get('thinking', '')
                    reply_text = parsed.get('content', raw_reply)
                except Exception:
                    pass

            messages.append({'role': 'assistant', 'content': reply_text})

            if db_chat_id:
                cur.execute(
                    f"UPDATE {SCHEMA}.chat_history SET messages=%s, updated_at=NOW() WHERE id=%s",
                    (json.dumps(messages), str(db_chat_id))
                )
            else:
                cur.execute(
                    f"INSERT INTO {SCHEMA}.chat_history (user_id, title, messages) VALUES (%s, %s, %s) RETURNING id",
                    (user_id, title, json.dumps(messages))
                )
                db_chat_id = cur.fetchone()[0]

            conn.commit()
            limit_info = get_limit_info(cur, user_id)

            result = {
                'ok': True,
                'reply': reply_text,
                'chat_id': str(db_chat_id),
                'messages': messages,
                'limit': limit_info,
            }
            if thinking_text:
                result['thinking'] = thinking_text

            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps(result)}

        # --- GET LIMIT ---
        elif action == 'get_limit':
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'ok': True, 'limit': get_limit_info(cur, user_id)})}

        # --- GET HISTORY ---
        elif action == 'get_history':
            cur.execute(
                f"SELECT id, title, created_at, updated_at FROM {SCHEMA}.chat_history WHERE user_id=%s ORDER BY updated_at DESC LIMIT 50",
                (user_id,)
            )
            rows = cur.fetchall()
            chats = [{'id': str(r[0]), 'title': r[1], 'created_at': str(r[2]), 'updated_at': str(r[3])} for r in rows]
            limit_info = get_limit_info(cur, user_id)
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'ok': True, 'chats': chats, 'limit': limit_info})}

        # --- GET CHAT ---
        elif action == 'get_chat':
            chat_id = body.get('chat_id')
            cur.execute(
                f"SELECT id, title, messages, created_at FROM {SCHEMA}.chat_history WHERE id=%s AND user_id=%s",
                (chat_id, user_id)
            )
            row = cur.fetchone()
            if not row:
                return {'statusCode': 404, 'headers': CORS, 'body': json.dumps({'error': 'Chat not found'})}
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({
                'ok': True,
                'chat': {'id': str(row[0]), 'title': row[1], 'messages': row[2], 'created_at': str(row[3])}
            })}

        # --- DELETE CHAT ---
        elif action == 'delete_chat':
            chat_id = body.get('chat_id')
            cur.execute(f"DELETE FROM {SCHEMA}.chat_history WHERE id=%s AND user_id=%s", (chat_id, user_id))
            conn.commit()
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'ok': True})}

        return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Unknown action'})}

    finally:
        cur.close()
        conn.close()
