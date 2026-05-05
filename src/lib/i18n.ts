export type Lang = 'ru' | 'en';

export const t = {
  ru: {
    // Auth
    signIn: 'Войти',
    enterEmail: 'Введите email',
    enterCode: 'Введите код',
    emailPlaceholder: 'your@email.com',
    codeSent: 'Код отправлен на',
    getCode: 'Получить код',
    sending: 'Отправляем...',
    continue: 'Продолжить',
    checking: 'Проверяем...',
    back: '← Назад',
    errorEmail: 'Введите корректный email',
    errorCode: 'Введите 6-значный код',
    poweredBy: '~1T параметров · Oxiwis',
    codeLabel: 'Код подтверждения',

    // Sidebar / Nav
    newChat: 'Новый чат',
    chat: 'Чат',
    history: 'История',
    profile: 'Профиль',
    logout: 'Выйти',
    recent: 'Последние',
    dialogs: 'Диалоги',

    // Chat
    chatPlaceholder: 'Написать OxiwisAI...',
    send: 'Отправить',
    thinking: 'Рассуждение',
    thinkingMode: 'Режим рассуждения',
    thinkingOn: 'Вкл',
    thinkingOff: 'Выкл',
    thinkingProcess: 'Процесс рассуждения',
    typing: 'OxiwisAI думает...',
    noChats: 'Начните первый диалог',
    limitReached: 'Достигнут дневной лимит 256 запросов. Обновится в полночь по МСК.',
    requestsLeft: 'запросов осталось',

    // History
    historyTitle: 'История диалогов',
    historyEmpty: 'Нет сохранённых диалогов',
    deleteChat: 'Удалить',
    openChat: 'Открыть',

    // Profile
    profileTitle: 'Профиль',
    yourName: 'Ваше имя',
    yourEmail: 'Email',
    save: 'Сохранить',
    saving: 'Сохраняем...',
    saved: 'Сохранено',
    memberSince: 'Участник с',
    dailyUsage: 'Использование сегодня',
    of: 'из',
    requests: 'запросов',

    // Lang
    language: 'Язык',
  },
  en: {
    // Auth
    signIn: 'Sign In',
    enterEmail: 'Enter your email',
    enterCode: 'Enter code',
    emailPlaceholder: 'your@email.com',
    codeSent: 'Code sent to',
    getCode: 'Get Code',
    sending: 'Sending...',
    continue: 'Continue',
    checking: 'Checking...',
    back: '← Back',
    errorEmail: 'Enter a valid email',
    errorCode: 'Enter 6-digit code',
    poweredBy: '~1T parameters · Oxiwis',
    codeLabel: 'Verification code',

    // Sidebar / Nav
    newChat: 'New Chat',
    chat: 'Chat',
    history: 'History',
    profile: 'Profile',
    logout: 'Logout',
    recent: 'Recent',
    dialogs: 'Dialogs',

    // Chat
    chatPlaceholder: 'Message OxiwisAI...',
    send: 'Send',
    thinking: 'Thinking',
    thinkingMode: 'Thinking Mode',
    thinkingOn: 'On',
    thinkingOff: 'Off',
    thinkingProcess: 'Reasoning process',
    typing: 'OxiwisAI is thinking...',
    noChats: 'Start your first conversation',
    limitReached: 'Daily limit of 256 requests reached. Resets at midnight MSK.',
    requestsLeft: 'requests left',

    // History
    historyTitle: 'Chat History',
    historyEmpty: 'No saved conversations',
    deleteChat: 'Delete',
    openChat: 'Open',

    // Profile
    profileTitle: 'Profile',
    yourName: 'Your name',
    yourEmail: 'Email',
    save: 'Save',
    saving: 'Saving...',
    saved: 'Saved',
    memberSince: 'Member since',
    dailyUsage: "Today's usage",
    of: 'of',
    requests: 'requests',

    // Lang
    language: 'Language',
  },
} as const;

export type TKeys = keyof typeof t['ru'];
