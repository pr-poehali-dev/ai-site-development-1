import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '@/lib/api';
import { t, Lang } from '@/lib/i18n';
import Icon from '@/components/ui/icon';

// ─── Types ────────────────────────────────────────────────────────────────────
interface User { id: string; email: string; name: string; created_at?: string }
interface Message { role: 'user' | 'assistant'; content: string; thinking?: string }
interface Chat { id: string; title: string; updated_at: string }
interface LimitInfo { used: number; limit: number; remaining: number }
type Tab = 'chat' | 'history' | 'profile';
type AuthStep = 'email' | 'code';

// ─── Logo ────────────────────────────────────────────────────────────────────
const LOGO_URL = 'https://cdn.poehali.dev/projects/bc51261c-a863-4d06-a23f-71157a55b74b/bucket/7e5e7698-9fd5-4062-aea0-5c3605825c09.jpg';

// ─── Auth Page ───────────────────────────────────────────────────────────────
function AuthPage({ onAuth, lang, onLangToggle }: {
  onAuth: (user: User, token: string) => void;
  lang: Lang;
  onLangToggle: () => void;
}) {
  const T = t[lang];
  const [step, setStep] = useState<AuthStep>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSendCode = async () => {
    if (!email || !email.includes('@')) { setError(T.errorEmail); return; }
    setLoading(true); setError('');
    const res = await api.sendCode(email);
    setLoading(false);
    if (res.ok) setStep('code');
    else setError(res.error || 'Error');
  };

  const handleLogin = async () => {
    if (code.length !== 6) { setError(T.errorCode); return; }
    setLoading(true); setError('');
    const res = await api.login(email, code);
    setLoading(false);
    if (res.ok) {
      localStorage.setItem('oxiwis_token', res.token);
      onAuth(res.user, res.token);
    } else {
      setError(res.error || 'Error');
    }
  };

  return (
    <div className="min-h-screen bg-mesh bg-grid flex items-center justify-center p-4 relative">
      <div className="fixed top-1/3 left-1/3 w-[500px] h-[500px] bg-white/[0.015] rounded-full blur-[100px] pointer-events-none" />
      <div className="fixed bottom-1/4 right-1/4 w-72 h-72 bg-white/[0.01] rounded-full blur-[80px] pointer-events-none" />

      {/* Lang toggle */}
      <button
        onClick={onLangToggle}
        className="fixed top-5 right-5 glass px-3 py-1.5 rounded-lg text-white/40 hover:text-white text-xs tracking-widest uppercase transition-all"
      >
        {lang === 'ru' ? 'EN' : 'RU'}
      </button>

      <div className="w-full max-w-[400px] animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="inline-block mb-5">
            <img src={LOGO_URL} alt="OxiwisAI" className="w-16 h-16 rounded-2xl object-cover animate-glow-pulse" />
          </div>
          <h1 className="font-display text-5xl font-light gradient-text tracking-wide mb-1">OxiwisAI</h1>
          <p className="text-white/25 text-[10px] tracking-[5px] uppercase">by Oxiwis</p>
        </div>

        <div className="glass-strong rounded-3xl p-8">
          {step === 'email' && (
            <div className="space-y-5 animate-scale-in">
              <div>
                <label className="block text-white/40 text-[10px] uppercase tracking-[3px] mb-2.5">{T.enterEmail}</label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSendCode()}
                  placeholder={T.emailPlaceholder}
                  className="input-glass w-full px-4 py-3.5 rounded-xl text-sm"
                  autoFocus
                />
              </div>
              {error && <p className="text-red-400/80 text-xs">{error}</p>}
              <button onClick={handleSendCode} disabled={loading} className="btn-primary w-full py-3.5 rounded-xl text-sm font-medium">
                {loading ? T.sending : T.getCode}
              </button>
            </div>
          )}

          {step === 'code' && (
            <div className="space-y-5 animate-scale-in">
              <div className="text-center">
                <p className="text-white/40 text-xs mb-1">{T.codeSent}</p>
                <p className="text-white text-sm font-medium">{email}</p>
              </div>
              <div>
                <label className="block text-white/40 text-[10px] uppercase tracking-[3px] mb-2.5">{T.codeLabel}</label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={code}
                  onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  onKeyDown={e => e.key === 'Enter' && handleLogin()}
                  placeholder="000000"
                  className="input-glass w-full px-4 py-3.5 rounded-xl text-center text-xl tracking-[10px] font-mono"
                  autoFocus
                />
              </div>
              {error && <p className="text-red-400/80 text-xs text-center">{error}</p>}
              <button onClick={handleLogin} disabled={loading} className="btn-primary w-full py-3.5 rounded-xl text-sm font-medium">
                {loading ? T.checking : T.signIn}
              </button>
              <button onClick={() => { setStep('email'); setCode(''); setError(''); }} className="btn-ghost w-full py-2.5 rounded-xl text-xs">
                {T.back}
              </button>
            </div>
          )}
        </div>

        <p className="text-center text-white/15 text-xs mt-6 tracking-wide">{T.poweredBy}</p>
      </div>
    </div>
  );
}

// ─── Sidebar ─────────────────────────────────────────────────────────────────
function Sidebar({ activeTab, onTabChange, user, chats, activeChatId, onChatSelect, onNewChat, onDeleteChat, onLogout, collapsed, onToggle, lang, onLangToggle, limit }: {
  activeTab: Tab; onTabChange: (t: Tab) => void;
  user: User; chats: Chat[]; activeChatId: string | null;
  onChatSelect: (id: string) => void; onNewChat: () => void;
  onDeleteChat: (id: string) => void; onLogout: () => void;
  collapsed: boolean; onToggle: () => void;
  lang: Lang; onLangToggle: () => void;
  limit: LimitInfo | null;
}) {
  const T = t[lang];
  const navItems: { tab: Tab; icon: string; label: string }[] = [
    { tab: 'chat', icon: 'MessageSquare', label: T.chat },
    { tab: 'history', icon: 'Clock', label: T.history },
    { tab: 'profile', icon: 'User', label: T.profile },
  ];
  const limitPct = limit ? Math.min(100, Math.round((limit.used / limit.limit) * 100)) : 0;

  return (
    <aside className={`flex flex-col h-full glass border-r border-white/[0.06] transition-all duration-300 ${collapsed ? 'w-16' : 'w-64'}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/[0.06]">
        {!collapsed && (
          <div className="flex items-center gap-2.5">
            <img src={LOGO_URL} alt="logo" className="w-7 h-7 rounded-lg object-cover" />
            <div>
              <div className="font-display text-base text-white/90 leading-none">OxiwisAI</div>
              <div className="text-white/25 text-[8px] tracking-[2px] uppercase">Oxiwis</div>
            </div>
          </div>
        )}
        <button onClick={onToggle} className="w-8 h-8 flex items-center justify-center rounded-lg text-white/30 hover:text-white transition-all">
          <Icon name={collapsed ? 'PanelLeftOpen' : 'PanelLeftClose'} size={15} />
        </button>
      </div>

      {/* New Chat */}
      <div className="p-3">
        <button
          onClick={() => { onNewChat(); onTabChange('chat'); }}
          className={`btn-ghost w-full rounded-xl flex items-center gap-2 ${collapsed ? 'justify-center p-2.5' : 'px-3 py-2.5'}`}
        >
          <Icon name="Plus" size={15} />
          {!collapsed && <span className="text-sm">{T.newChat}</span>}
        </button>
      </div>

      {/* Nav */}
      <nav className="px-3 space-y-0.5">
        {navItems.map(({ tab, icon, label }) => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            className={`w-full flex items-center gap-2.5 rounded-xl transition-all duration-200 text-sm
              ${collapsed ? 'justify-center p-2.5' : 'px-3 py-2.5'}
              ${activeTab === tab ? 'bg-white/[0.08] text-white border border-white/10' : 'text-white/35 hover:text-white/70 hover:bg-white/[0.04]'}`}
          >
            <Icon name={icon} size={15} />
            {!collapsed && <span>{label}</span>}
          </button>
        ))}
      </nav>

      {/* Recent chats */}
      {!collapsed && chats.length > 0 && (
        <div className="flex-1 overflow-y-auto px-3 mt-4">
          <p className="text-white/20 text-[9px] uppercase tracking-[3px] px-2 mb-2">{T.recent}</p>
          <div className="space-y-0.5">
            {chats.slice(0, 8).map(chat => (
              <div key={chat.id} className="group flex items-center gap-1">
                <button
                  onClick={() => { onChatSelect(chat.id); onTabChange('chat'); }}
                  className={`flex-1 text-left px-3 py-2 rounded-xl text-xs transition-all truncate ${activeChatId === chat.id ? 'bg-white/[0.08] text-white' : 'text-white/35 hover:text-white/65 hover:bg-white/[0.04]'}`}
                >
                  {chat.title}
                </button>
                <button
                  onClick={() => onDeleteChat(chat.id)}
                  className="opacity-0 group-hover:opacity-100 w-6 h-6 flex items-center justify-center rounded-lg text-white/25 hover:text-red-400 transition-all"
                >
                  <Icon name="Trash2" size={11} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex-1" />

      {/* Limit bar */}
      {!collapsed && limit && (
        <div className="px-4 py-3 border-t border-white/[0.06]">
          <div className="flex justify-between text-[10px] text-white/30 mb-1.5">
            <span>{T.requests}</span>
            <span>{limit.used}/{limit.limit}</span>
          </div>
          <div className="h-1 bg-white/[0.07] rounded-full overflow-hidden">
            <div
              className="h-full bg-white/40 rounded-full transition-all duration-500"
              style={{ width: `${limitPct}%` }}
            />
          </div>
        </div>
      )}

      {/* Lang + Logout */}
      <div className="p-3 border-t border-white/[0.06] space-y-1">
        <button
          onClick={onLangToggle}
          className={`btn-ghost w-full rounded-xl flex items-center gap-2 ${collapsed ? 'justify-center p-2.5' : 'px-3 py-2.5'}`}
        >
          <Icon name="Globe" size={14} />
          {!collapsed && <span className="text-xs">{lang === 'ru' ? 'English' : 'Русский'}</span>}
        </button>
        <button
          onClick={onLogout}
          className={`btn-ghost w-full rounded-xl flex items-center gap-2 text-red-400/60 border-transparent hover:text-red-400 hover:border-red-500/15 ${collapsed ? 'justify-center p-2.5' : 'px-3 py-2.5'}`}
        >
          <Icon name="LogOut" size={14} />
          {!collapsed && <span className="text-xs">{T.logout}</span>}
        </button>
      </div>
    </aside>
  );
}

// ─── Message bubble ───────────────────────────────────────────────────────────
function MessageBubble({ msg, lang }: { msg: Message; lang: Lang }) {
  const T = t[lang];
  const [thinkingOpen, setThinkingOpen] = useState(false);
  const isUser = msg.role === 'user';

  return (
    <div className={`flex gap-3 message-appear ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-7 h-7 flex-shrink-0 rounded-xl overflow-hidden mt-0.5">
          <img src={LOGO_URL} alt="AI" className="w-full h-full object-cover" />
        </div>
      )}
      <div className={`max-w-[75%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-2`}>
        {msg.thinking && (
          <div className="w-full">
            <button
              onClick={() => setThinkingOpen(!thinkingOpen)}
              className="flex items-center gap-1.5 text-white/30 text-xs hover:text-white/50 transition-all mb-1.5"
            >
              <Icon name="Brain" size={12} />
              <span>{T.thinkingProcess}</span>
              <Icon name={thinkingOpen ? 'ChevronUp' : 'ChevronDown'} size={11} />
            </button>
            {thinkingOpen && (
              <div className="glass rounded-xl p-3 text-white/40 text-xs leading-relaxed whitespace-pre-wrap border-l-2 border-white/10 animate-fade-in">
                {msg.thinking}
              </div>
            )}
          </div>
        )}
        <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? 'bg-white text-black rounded-tr-md'
            : 'glass text-white/90 rounded-tl-md'
        }`}>
          {msg.content}
        </div>
      </div>
    </div>
  );
}

// ─── Chat View ────────────────────────────────────────────────────────────────
function ChatView({ user, activeChatId, onChatCreated, onLimitUpdate, lang, thinkingMode, onThinkingToggle, limit }: {
  user: User; activeChatId: string | null;
  onChatCreated: (id: string) => void;
  onLimitUpdate: (l: LimitInfo) => void;
  lang: Lang; thinkingMode: boolean;
  onThinkingToggle: () => void;
  limit: LimitInfo | null;
}) {
  const T = t[lang];
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [limitHit, setLimitHit] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const currentChatId = useRef<string | null>(activeChatId);

  useEffect(() => {
    currentChatId.current = activeChatId;
    if (activeChatId) {
      loadChat(activeChatId);
    } else {
      setMessages([]);
      setLimitHit(false);
    }
  }, [activeChatId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const loadChat = async (id: string) => {
    const res = await api.getChat(id);
    if (res.ok) setMessages(res.chat.messages || []);
  };

  const handleSend = async () => {
    if (!input.trim() || loading || limitHit) return;
    const text = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    const res = await api.sendMessage(text, currentChatId.current || undefined, thinkingMode);
    setLoading(false);

    if (res.error === 'Daily limit reached') {
      setLimitHit(true);
      setMessages(prev => prev.slice(0, -1));
      return;
    }

    if (res.ok) {
      const aiMsg: Message = { role: 'assistant', content: res.reply };
      if (res.thinking) aiMsg.thinking = res.thinking;
      setMessages(prev => [...prev, aiMsg]);
      if (!currentChatId.current) {
        currentChatId.current = res.chat_id;
        onChatCreated(res.chat_id);
      }
      if (res.limit) onLimitUpdate(res.limit);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full">
      {/* Thinking mode toggle */}
      <div className="flex items-center justify-end px-5 py-3 border-b border-white/[0.05]">
        <button
          onClick={onThinkingToggle}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs transition-all duration-300 border ${
            thinkingMode
              ? 'bg-white/10 border-white/20 text-white'
              : 'bg-transparent border-white/08 text-white/35 hover:text-white/60 hover:border-white/15'
          }`}
        >
          <Icon name="Brain" size={13} />
          <span>{T.thinkingMode}</span>
          <span className={`ml-1 font-medium ${thinkingMode ? 'text-white' : 'text-white/30'}`}>
            {thinkingMode ? T.thinkingOn : T.thinkingOff}
          </span>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-6 space-y-5">
        {isEmpty && !loading && (
          <div className="h-full flex flex-col items-center justify-center text-center animate-fade-in">
            <img src={LOGO_URL} alt="OxiwisAI" className="w-14 h-14 rounded-2xl object-cover opacity-40 mb-5" />
            <p className="font-display text-3xl font-light text-white/25 mb-2">OxiwisAI</p>
            <p className="text-white/20 text-sm">{T.noChats}</p>
            {limit && (
              <p className="text-white/15 text-xs mt-3">{limit.remaining} {T.requestsLeft}</p>
            )}
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} lang={lang} />
        ))}
        {loading && (
          <div className="flex gap-3 justify-start">
            <div className="w-7 h-7 rounded-xl overflow-hidden flex-shrink-0">
              <img src={LOGO_URL} alt="AI" className="w-full h-full object-cover" />
            </div>
            <div className="glass px-4 py-3 rounded-2xl rounded-tl-md flex items-center gap-2">
              {[0, 1, 2].map(i => (
                <span
                  key={i}
                  className="w-1.5 h-1.5 bg-white/40 rounded-full animate-typing"
                  style={{ animationDelay: `${i * 0.2}s` }}
                />
              ))}
            </div>
          </div>
        )}
        {limitHit && (
          <div className="glass border border-red-500/20 rounded-2xl px-4 py-3 text-red-400/80 text-sm text-center animate-fade-in">
            {T.limitReached}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 pb-5 pt-3 border-t border-white/[0.05]">
        <div className="glass-strong rounded-2xl flex items-end gap-3 px-4 py-3">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={T.chatPlaceholder}
            rows={1}
            disabled={loading || limitHit}
            className="flex-1 bg-transparent text-white/90 text-sm placeholder-white/25 resize-none outline-none leading-relaxed"
            style={{ maxHeight: '160px' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading || limitHit}
            className="w-8 h-8 flex-shrink-0 rounded-xl flex items-center justify-center transition-all duration-200 disabled:opacity-25 bg-white hover:bg-white/90 active:scale-95"
          >
            <Icon name="ArrowUp" size={15} className="text-black" />
          </button>
        </div>
        <p className="text-center text-white/15 text-[10px] mt-2">Shift+Enter — новая строка</p>
      </div>
    </div>
  );
}

// ─── History View ─────────────────────────────────────────────────────────────
function HistoryView({ chats, onOpen, onDelete, lang }: {
  chats: Chat[]; onOpen: (id: string) => void;
  onDelete: (id: string) => void; lang: Lang;
}) {
  const T = t[lang];

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-5 border-b border-white/[0.05]">
        <h2 className="font-display text-2xl font-light text-white/80">{T.historyTitle}</h2>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {chats.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-white/25 text-sm">{T.historyEmpty}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {chats.map(chat => (
              <div key={chat.id} className="glass glass-hover rounded-2xl px-4 py-3.5 flex items-center gap-3 group">
                <Icon name="MessageSquare" size={14} className="text-white/25 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-white/80 text-sm truncate">{chat.title}</p>
                  <p className="text-white/25 text-xs mt-0.5">
                    {new Date(chat.updated_at).toLocaleDateString(lang === 'ru' ? 'ru-RU' : 'en-US', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-all">
                  <button
                    onClick={() => onOpen(chat.id)}
                    className="text-white/40 hover:text-white text-xs px-2.5 py-1 glass rounded-lg transition-all"
                  >
                    {T.openChat}
                  </button>
                  <button
                    onClick={() => onDelete(chat.id)}
                    className="text-red-400/50 hover:text-red-400 w-7 h-7 flex items-center justify-center glass rounded-lg transition-all"
                  >
                    <Icon name="Trash2" size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Profile View ─────────────────────────────────────────────────────────────
function ProfileView({ user, onUserUpdate, lang, limit }: {
  user: User; onUserUpdate: (u: User) => void;
  lang: Lang; limit: LimitInfo | null;
}) {
  const T = t[lang];
  const [name, setName] = useState(user.name);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle');

  const handleSave = async () => {
    if (!name.trim() || name === user.name) return;
    setSaveState('saving');
    const res = await api.updateName(name.trim());
    if (res.ok) {
      onUserUpdate({ ...user, name: name.trim() });
      setSaveState('saved');
      setTimeout(() => setSaveState('idle'), 2000);
    } else {
      setSaveState('idle');
    }
  };

  const limitPct = limit ? Math.min(100, Math.round((limit.used / limit.limit) * 100)) : 0;

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-5 border-b border-white/[0.05]">
        <h2 className="font-display text-2xl font-light text-white/80">{T.profileTitle}</h2>
      </div>
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-md space-y-5">
          {/* Avatar */}
          <div className="flex items-center gap-4 glass rounded-2xl p-4">
            <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center text-white font-display text-xl font-light">
              {user.name[0]?.toUpperCase()}
            </div>
            <div>
              <p className="text-white font-medium">{user.name}</p>
              <p className="text-white/35 text-sm">{user.email}</p>
            </div>
          </div>

          {/* Name edit */}
          <div className="glass rounded-2xl p-4 space-y-3">
            <label className="text-white/40 text-[10px] uppercase tracking-[3px]">{T.yourName}</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSave()}
              className="input-glass w-full px-4 py-3 rounded-xl text-sm"
            />
            <button
              onClick={handleSave}
              disabled={saveState === 'saving' || name === user.name}
              className="btn-primary px-5 py-2.5 rounded-xl text-sm disabled:opacity-40"
            >
              {saveState === 'saving' ? T.saving : saveState === 'saved' ? '✓ ' + T.saved : T.save}
            </button>
          </div>

          {/* Usage */}
          {limit && (
            <div className="glass rounded-2xl p-4 space-y-3">
              <div className="flex justify-between items-center">
                <p className="text-white/40 text-[10px] uppercase tracking-[3px]">{T.dailyUsage}</p>
                <p className="text-white/50 text-sm">{limit.used} {T.of} {limit.limit} {T.requests}</p>
              </div>
              <div className="h-2 bg-white/[0.07] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${limitPct > 80 ? 'bg-red-400/60' : 'bg-white/40'}`}
                  style={{ width: `${limitPct}%` }}
                />
              </div>
              <p className="text-white/25 text-xs">{limit.remaining} {T.requestsLeft}</p>
            </div>
          )}

          {/* Member since */}
          {user.created_at && (
            <p className="text-white/20 text-xs px-1">
              {T.memberSince}: {new Date(user.created_at).toLocaleDateString(lang === 'ru' ? 'ru-RU' : 'en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function Index() {
  const [lang, setLang] = useState<Lang>(() => (localStorage.getItem('oxiwis_lang') as Lang) || 'ru');
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>('chat');
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [limit, setLimit] = useState<LimitInfo | null>(null);
  const [thinkingMode, setThinkingMode] = useState(false);

  const toggleLang = useCallback(() => {
    setLang(prev => {
      const next = prev === 'ru' ? 'en' : 'ru';
      localStorage.setItem('oxiwis_lang', next);
      return next;
    });
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('oxiwis_token');
    if (!token) { setAuthChecked(true); return; }
    api.getMe().then(res => {
      if (res.ok) {
        setUser(res.user);
        loadHistory();
        loadLimit();
      } else {
        localStorage.removeItem('oxiwis_token');
      }
      setAuthChecked(true);
    });
  }, []);

  const loadHistory = async () => {
    const res = await api.getHistory();
    if (res.ok) {
      setChats(res.chats || []);
      if (res.limit) setLimit(res.limit);
    }
  };

  const loadLimit = async () => {
    const res = await api.getLimit();
    if (res.ok) setLimit(res.limit);
  };

  const handleAuth = (u: User) => {
    setUser(u);
    loadHistory();
    loadLimit();
  };

  const handleLogout = async () => {
    await api.logout();
    localStorage.removeItem('oxiwis_token');
    setUser(null);
    setChats([]);
    setActiveChatId(null);
    setLimit(null);
  };

  const handleNewChat = () => {
    setActiveChatId(null);
    setActiveTab('chat');
  };

  const handleChatCreated = (id: string) => {
    setActiveChatId(id);
    loadHistory();
  };

  const handleDeleteChat = async (id: string) => {
    await api.deleteChat(id);
    setChats(prev => prev.filter(c => c.id !== id));
    if (activeChatId === id) setActiveChatId(null);
  };

  const handleChatSelect = (id: string) => {
    setActiveChatId(id);
    setActiveTab('chat');
  };

  if (!authChecked) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <div className="w-8 h-8 border border-white/20 border-t-white/60 rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <AuthPage onAuth={handleAuth} lang={lang} onLangToggle={toggleLang} />;
  }

  return (
    <div className="flex h-screen bg-mesh bg-grid overflow-hidden">
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        user={user}
        chats={chats}
        activeChatId={activeChatId}
        onChatSelect={handleChatSelect}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        onLogout={handleLogout}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(p => !p)}
        lang={lang}
        onLangToggle={toggleLang}
        limit={limit}
      />

      <main className="flex-1 min-w-0 flex flex-col">
        {activeTab === 'chat' && (
          <ChatView
            key={activeChatId || 'new'}
            user={user}
            activeChatId={activeChatId}
            onChatCreated={handleChatCreated}
            onLimitUpdate={(l) => { setLimit(l); loadHistory(); }}
            lang={lang}
            thinkingMode={thinkingMode}
            onThinkingToggle={() => setThinkingMode(p => !p)}
            limit={limit}
          />
        )}
        {activeTab === 'history' && (
          <HistoryView
            chats={chats}
            onOpen={handleChatSelect}
            onDelete={handleDeleteChat}
            lang={lang}
          />
        )}
        {activeTab === 'profile' && (
          <ProfileView
            user={user}
            onUserUpdate={setUser}
            lang={lang}
            limit={limit}
          />
        )}
      </main>
    </div>
  );
}
