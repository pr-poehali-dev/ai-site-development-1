import { useState } from 'react';
import { api } from '@/lib/api';
import Icon from '@/components/ui/icon';

type Step = 'email' | 'code' | 'register_info' | 'tfa';

interface AuthPageProps {
  onAuth: (user: { id: string; email: string; name: string; has_2fa: boolean }) => void;
}

export default function AuthPage({ onAuth }: AuthPageProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [enable2fa, setEnable2fa] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [pendingLogin, setPendingLogin] = useState<{ email: string; code: string } | null>(null);

  const handleSendCode = async () => {
    if (!email || !email.includes('@')) { setError('Введите корректный email'); return; }
    setLoading(true); setError('');
    const res = await api.sendCode(email, mode);
    setLoading(false);
    if (res.ok) setStep('code');
    else setError(res.error || 'Ошибка отправки кода');
  };

  const handleVerifyCode = async () => {
    if (code.length !== 6) { setError('Введите 6-значный код'); return; }
    setLoading(true); setError('');
    const res = await api.verifyCode(email, code);
    setLoading(false);
    if (!res.ok) { setError(res.error || 'Неверный код'); return; }
    if (mode === 'register') { setStep('register_info'); return; }
    // login
    const loginRes = await (async () => {
      setLoading(true);
      const r = await api.login(email, code);
      setLoading(false);
      return r;
    })();
    if (loginRes.require_2fa) {
      setPendingLogin({ email, code });
      setStep('tfa');
      return;
    }
    if (loginRes.ok) {
      localStorage.setItem('oxiwis_token', loginRes.token);
      onAuth(loginRes.user);
    } else {
      setError(loginRes.error || 'Ошибка входа');
    }
  };

  const handleRegister = async () => {
    if (!name.trim()) { setError('Введите имя'); return; }
    if (enable2fa && !password) { setError('Введите пароль для 2FA'); return; }
    setLoading(true); setError('');
    const res = await api.register(email, code, name, password, enable2fa);
    setLoading(false);
    if (res.ok) {
      localStorage.setItem('oxiwis_token', res.token);
      onAuth(res.user);
    } else {
      setError(res.error || 'Ошибка регистрации');
    }
  };

  const handleTfa = async () => {
    if (!password) { setError('Введите пароль'); return; }
    if (!pendingLogin) return;
    setLoading(true); setError('');
    const res = await api.login(pendingLogin.email, pendingLogin.code, password);
    setLoading(false);
    if (res.ok) {
      localStorage.setItem('oxiwis_token', res.token);
      onAuth(res.user);
    } else {
      setError(res.error || 'Неверный пароль');
    }
  };

  const codeDigits = code.split('');

  return (
    <div className="min-h-screen bg-mesh bg-grid flex items-center justify-center p-4">
      {/* Glow orbs */}
      <div className="fixed top-1/4 left-1/4 w-96 h-96 bg-white/[0.02] rounded-full blur-3xl pointer-events-none" />
      <div className="fixed bottom-1/4 right-1/4 w-80 h-80 bg-white/[0.015] rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 glass rounded-2xl mb-6 animate-glow-pulse">
            <span className="font-display text-2xl font-light text-white/90">O</span>
          </div>
          <h1 className="font-display text-4xl font-light gradient-text mb-1">OxiwisAI</h1>
          <p className="text-white/30 text-xs tracking-[4px] uppercase font-body">by Oxiwis</p>
        </div>

        {/* Card */}
        <div className="glass-strong rounded-3xl p-8">
          {/* Mode Switch */}
          {step === 'email' && (
            <div className="flex glass rounded-2xl p-1 mb-8">
              {(['login', 'register'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => { setMode(m); setError(''); }}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${
                    mode === m ? 'bg-white text-black' : 'text-white/50 hover:text-white/80'
                  }`}
                >
                  {m === 'login' ? 'Войти' : 'Регистрация'}
                </button>
              ))}
            </div>
          )}

          {/* Steps */}
          {step === 'email' && (
            <div className="space-y-4 animate-scale-in">
              <div>
                <label className="block text-white/50 text-xs uppercase tracking-widest mb-2">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendCode()}
                  placeholder="your@email.com"
                  className="input-glass w-full px-4 py-3.5 rounded-xl text-sm"
                  autoFocus
                />
              </div>
              {error && <p className="text-red-400/80 text-sm">{error}</p>}
              <button onClick={handleSendCode} disabled={loading} className="btn-primary w-full py-3.5 rounded-xl text-sm">
                {loading ? 'Отправляем...' : 'Получить код'}
              </button>
            </div>
          )}

          {step === 'code' && (
            <div className="space-y-6 animate-scale-in">
              <div className="text-center">
                <p className="text-white/60 text-sm mb-1">Код отправлен на</p>
                <p className="text-white font-medium">{email}</p>
              </div>
              <div>
                <label className="block text-white/50 text-xs uppercase tracking-widest mb-3">Код подтверждения</label>
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  onKeyDown={(e) => e.key === 'Enter' && handleVerifyCode()}
                  placeholder="000000"
                  className="input-glass w-full px-4 py-3.5 rounded-xl text-sm text-center tracking-[12px] text-lg font-mono"
                  autoFocus
                />
              </div>
              {error && <p className="text-red-400/80 text-sm text-center">{error}</p>}
              <button onClick={handleVerifyCode} disabled={loading} className="btn-primary w-full py-3.5 rounded-xl text-sm">
                {loading ? 'Проверяем...' : 'Продолжить'}
              </button>
              <button onClick={() => { setStep('email'); setCode(''); setError(''); }} className="btn-ghost w-full py-2.5 rounded-xl text-xs">
                ← Назад
              </button>
            </div>
          )}

          {step === 'register_info' && (
            <div className="space-y-5 animate-scale-in">
              <div className="text-center mb-2">
                <p className="text-white/70 text-sm">Почти готово! Заполните профиль</p>
              </div>
              <div>
                <label className="block text-white/50 text-xs uppercase tracking-widest mb-2">Имя</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ваше имя"
                  className="input-glass w-full px-4 py-3.5 rounded-xl text-sm"
                  autoFocus
                />
              </div>

              {/* 2FA toggle */}
              <div className="glass rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <button
                    onClick={() => setEnable2fa(!enable2fa)}
                    className={`mt-0.5 w-10 h-6 rounded-full transition-all duration-300 flex-shrink-0 relative ${enable2fa ? 'bg-white' : 'bg-white/15'}`}
                  >
                    <span className={`absolute top-1 w-4 h-4 rounded-full transition-all duration-300 ${enable2fa ? 'left-5 bg-black' : 'left-1 bg-white/40'}`} />
                  </button>
                  <div>
                    <p className="text-white text-sm font-medium">Двухфакторная аутентификация</p>
                    <p className="text-white/40 text-xs mt-0.5">Защитит аккаунт паролем при каждом входе</p>
                  </div>
                </div>
                {enable2fa && (
                  <div className="mt-3">
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Придумайте пароль"
                      className="input-glass w-full px-4 py-3 rounded-xl text-sm"
                    />
                  </div>
                )}
              </div>

              {error && <p className="text-red-400/80 text-sm">{error}</p>}
              <button onClick={handleRegister} disabled={loading} className="btn-primary w-full py-3.5 rounded-xl text-sm">
                {loading ? 'Создаём аккаунт...' : 'Создать аккаунт'}
              </button>
            </div>
          )}

          {step === 'tfa' && (
            <div className="space-y-5 animate-scale-in">
              <div className="text-center">
                <div className="w-12 h-12 glass rounded-xl flex items-center justify-center mx-auto mb-4">
                  <Icon name="Shield" size={20} className="text-white/70" />
                </div>
                <p className="text-white/60 text-sm">Введите пароль для входа</p>
              </div>
              <div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleTfa()}
                  placeholder="Ваш пароль"
                  className="input-glass w-full px-4 py-3.5 rounded-xl text-sm"
                  autoFocus
                />
              </div>
              {error && <p className="text-red-400/80 text-sm text-center">{error}</p>}
              <button onClick={handleTfa} disabled={loading} className="btn-primary w-full py-3.5 rounded-xl text-sm">
                {loading ? 'Входим...' : 'Войти'}
              </button>
            </div>
          )}
        </div>

        <p className="text-center text-white/20 text-xs mt-6">
          OxiwisAI · ~1T параметров · Oxiwis
        </p>
      </div>
    </div>
  );
}
