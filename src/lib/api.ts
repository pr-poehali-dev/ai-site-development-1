const AUTH_URL = 'https://functions.poehali.dev/a30e9f55-30d0-43df-8af2-9ad971f594c6';
const CHAT_URL = 'https://functions.poehali.dev/4f8f95e7-d927-4831-b0b3-59c9acec56ba';

function getToken(): string {
  return localStorage.getItem('oxiwis_token') || '';
}

async function callAuth(body: object) {
  const res = await fetch(AUTH_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
    body: JSON.stringify(body),
  });
  return res.json();
}

async function callChat(body: object) {
  const res = await fetch(CHAT_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
    body: JSON.stringify(body),
  });
  return res.json();
}

export const api = {
  sendCode: (email: string, purpose: 'login' | 'register') =>
    callAuth({ action: 'send_code', email, purpose }),

  verifyCode: (email: string, code: string) =>
    callAuth({ action: 'verify_code', email, code }),

  register: (email: string, code: string, name: string, password: string, enable_2fa: boolean) =>
    callAuth({ action: 'register', email, code, name, password, enable_2fa }),

  login: (email: string, code: string, password?: string) =>
    callAuth({ action: 'login', email, code, password }),

  getMe: () => callAuth({ action: 'get_me' }),

  updateProfile: (data: { name?: string; password?: string; enable_2fa?: boolean }) =>
    callAuth({ action: 'update_profile', ...data }),

  logout: () => callAuth({ action: 'logout' }),

  sendMessage: (message: string, chat_id?: string) =>
    callChat({ action: 'send_message', message, chat_id }),

  getHistory: () => callChat({ action: 'get_history' }),

  getChat: (chat_id: string) => callChat({ action: 'get_chat', chat_id }),

  deleteChat: (chat_id: string) => callChat({ action: 'delete_chat', chat_id }),
};
