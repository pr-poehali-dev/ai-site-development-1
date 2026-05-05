"""
Chat функция: отправка сообщений в OxiwisAI API, сохранение истории.
Действия: send_message, get_history, get_chat, delete_chat
"""
import json
import os
import urllib.request
import psycopg2

SCHEMA = os.environ.get('MAIN_DB_SCHEMA', 'public')
CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-User-Id, X-Auth-Token, X-Session-Id, X-Authorization',
}

OXIWIS_API_URL = 'https://jpdwcpxlotztzrqcgfeg.supabase.co/functions/v1/v1-chat'
OXIWIS_API_KEY = 'ypr_OBqnJxMDLkBWn3IztUOX6dcuW8hH3AfeUHrOAku7X3k'


def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def get_user_from_token(cur, token: str):
    cur.execute(
        f"SELECT u.id, u.email, u.name FROM {SCHEMA}.sessions s JOIN {SCHEMA}.users u ON s.user_id=u.id WHERE s.token=%s AND s.expires_at > NOW()",
        (token,)
    )
    return cur.fetchone()


def call_oxiwis(messages: list) -> str:
    payload = json.dumps({
        'model': 'OxiwisAI',
        'messages': messages,
        'stream': False
    }).encode('utf-8')

    req = urllib.request.Request(
        OXIWIS_API_URL,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {OXIWIS_API_KEY}',
        },
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    if 'choices' in data and data['choices']:
        return data['choices'][0]['message']['content']
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
            return {'statusCode': 401, 'headers': CORS, 'body': json.dumps({'error': 'Не авторизован'})}

        user_id = user[0]

        # --- SEND MESSAGE ---
        if action == 'send_message':
            chat_id = body.get('chat_id')
            user_message = body.get('message', '').strip()
            if not user_message:
                return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Сообщение пустое'})}

            if chat_id:
                cur.execute(
                    f"SELECT id, messages, title FROM {SCHEMA}.chat_history WHERE id=%s AND user_id=%s",
                    (chat_id, str(user_id))
                )
                chat_row = cur.fetchone()
                if not chat_row:
                    return {'statusCode': 404, 'headers': CORS, 'body': json.dumps({'error': 'Чат не найден'})}
                db_chat_id, existing_messages, title = chat_row
                messages = existing_messages if isinstance(existing_messages, list) else []
            else:
                messages = []
                title = user_message[:60]
                db_chat_id = None

            messages.append({'role': 'user', 'content': user_message})
            ai_reply = call_oxiwis(messages)
            messages.append({'role': 'assistant', 'content': ai_reply})

            if db_chat_id:
                cur.execute(
                    f"UPDATE {SCHEMA}.chat_history SET messages=%s, updated_at=NOW() WHERE id=%s",
                    (json.dumps(messages), str(db_chat_id))
                )
            else:
                cur.execute(
                    f"INSERT INTO {SCHEMA}.chat_history (user_id, title, messages) VALUES (%s, %s, %s) RETURNING id",
                    (str(user_id), title, json.dumps(messages))
                )
                db_chat_id = cur.fetchone()[0]

            conn.commit()
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({
                'ok': True, 'reply': ai_reply, 'chat_id': str(db_chat_id), 'messages': messages
            })}

        # --- GET HISTORY ---
        elif action == 'get_history':
            cur.execute(
                f"SELECT id, title, created_at, updated_at FROM {SCHEMA}.chat_history WHERE user_id=%s ORDER BY updated_at DESC LIMIT 50",
                (str(user_id),)
            )
            rows = cur.fetchall()
            chats = [{'id': str(r[0]), 'title': r[1], 'created_at': str(r[2]), 'updated_at': str(r[3])} for r in rows]
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'ok': True, 'chats': chats})}

        # --- GET CHAT ---
        elif action == 'get_chat':
            chat_id = body.get('chat_id')
            cur.execute(
                f"SELECT id, title, messages, created_at FROM {SCHEMA}.chat_history WHERE id=%s AND user_id=%s",
                (chat_id, str(user_id))
            )
            row = cur.fetchone()
            if not row:
                return {'statusCode': 404, 'headers': CORS, 'body': json.dumps({'error': 'Чат не найден'})}
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({
                'ok': True, 'chat': {'id': str(row[0]), 'title': row[1], 'messages': row[2], 'created_at': str(row[3])}
            })}

        # --- DELETE CHAT ---
        elif action == 'delete_chat':
            chat_id = body.get('chat_id')
            cur.execute(f"DELETE FROM {SCHEMA}.chat_history WHERE id=%s AND user_id=%s", (chat_id, str(user_id)))
            conn.commit()
            return {'statusCode': 200, 'headers': CORS, 'body': json.dumps({'ok': True})}

        return {'statusCode': 400, 'headers': CORS, 'body': json.dumps({'error': 'Неизвестное действие'})}

    finally:
        cur.close()
        conn.close()
