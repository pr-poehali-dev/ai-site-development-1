"""
API для работы с историей чатов OxiwisAI: сохранение, получение и удаление диалогов.
"""
import json
import os
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


def get_user_id(cur, token: str):
    cur.execute(
        f"SELECT u.id FROM {SCHEMA}.sessions s JOIN {SCHEMA}.users u ON s.user_id=u.id WHERE s.token=%s AND s.expires_at > NOW()",
        (token,)
    )
    row = cur.fetchone()
    return row[0] if row else None


def handler(event: dict, context) -> dict:
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    token = event.get('headers', {}).get('X-Auth-Token', '')
    body = {}
    if event.get('body'):
        body = json.loads(event['body'])

    conn = get_conn()
    cur = conn.cursor()

    try:
        user_id = get_user_id(cur, token)
        if not user_id:
            return {'statusCode': 401, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Не авторизован'})}

        # GET / — список чатов
        if method == 'GET' and path.rstrip('/') in ('', '/'):
            cur.execute(
                f"SELECT id, title, created_at, updated_at FROM {SCHEMA}.chat_history WHERE user_id=%s ORDER BY updated_at DESC",
                (str(user_id),)
            )
            rows = cur.fetchall()
            chats = [{'id': str(r[0]), 'title': r[1], 'created_at': r[2].isoformat(), 'updated_at': r[3].isoformat()} for r in rows]
            return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'chats': chats})}

        # GET /{id} — конкретный чат
        elif method == 'GET':
            chat_id = path.strip('/').split('/')[-1]
            cur.execute(
                f"SELECT id, title, messages, created_at FROM {SCHEMA}.chat_history WHERE id=%s AND user_id=%s",
                (chat_id, str(user_id))
            )
            row = cur.fetchone()
            if not row:
                return {'statusCode': 404, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Чат не найден'})}
            return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'id': str(row[0]), 'title': row[1], 'messages': row[2], 'created_at': row[3].isoformat()})}

        # POST / — создать чат
        elif method == 'POST' and path.rstrip('/') in ('', '/'):
            title = body.get('title', 'Новый диалог')
            messages = body.get('messages', [])
            cur.execute(
                f"INSERT INTO {SCHEMA}.chat_history (user_id, title, messages) VALUES (%s, %s, %s) RETURNING id, created_at",
                (str(user_id), title, json.dumps(messages))
            )
            row = cur.fetchone()
            conn.commit()
            return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'id': str(row[0]), 'created_at': row[1].isoformat()})}

        # PUT /{id} — обновить чат
        elif method == 'PUT':
            chat_id = path.strip('/').split('/')[-1]
            title = body.get('title')
            messages = body.get('messages')
            if title:
                cur.execute(f"UPDATE {SCHEMA}.chat_history SET title=%s, updated_at=NOW() WHERE id=%s AND user_id=%s", (title, chat_id, str(user_id)))
            if messages is not None:
                cur.execute(f"UPDATE {SCHEMA}.chat_history SET messages=%s, updated_at=NOW() WHERE id=%s AND user_id=%s", (json.dumps(messages), chat_id, str(user_id)))
            conn.commit()
            return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': json.dumps({'ok': True})}

        return {'statusCode': 404, 'headers': CORS_HEADERS, 'body': json.dumps({'error': 'Not found'})}

    finally:
        cur.close()
        conn.close()
