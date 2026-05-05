const AUTH_URL = 'https://functions.poehali.dev/a30e9f55-30d0-43df-8af2-9ad971f594c6';
const CHAT_URL = 'https://functions.poehali.dev/4f8f95e7-d927-4831-b0b3-59c9acec56ba';

function getToken(): string {
  return localStorage.getItem('oxiwis_token') || '';
}

async function callAuth(body: object) {
  const token = getToken();
  const res = await fetch(AUTH_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  return res.json();
}

async function callChat(body: object) {
  const token = getToken();
  const res = await fetch(CHAT_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  return res.json();
}

export const api = {
  sendCode: (email: string) => callAuth({ action: 'send_code', email }),
  login: (email: string, code: string) => callAuth({ action: 'login', email, code }),
  getMe: () => callAuth({ action: 'get_me' }),
  updateName: (name: string) => callAuth({ action: 'update_name', name }),
  logout: () => callAuth({ action: 'logout' }),

  sendMessage: (message: string, chat_id?: string, thinking_mode?: boolean) =>
    callChat({ action: 'send_message', message, chat_id, thinking_mode: !!thinking_mode }),
  getHistory: () => callChat({ action: 'get_history' }),
  getChat: (chat_id: string) => callChat({ action: 'get_chat', chat_id }),
  deleteChat: (chat_id: string) => callChat({ action: 'delete_chat', chat_id }),
  getLimit: () => callChat({ action: 'get_limit' }),
};
