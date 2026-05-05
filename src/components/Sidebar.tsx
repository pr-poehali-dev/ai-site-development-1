import Icon from '@/components/ui/icon';

type Tab = 'chat' | 'history' | 'profile' | 'settings';

interface Chat {
  id: string;
  title: string;
  updated_at: string;
}

interface SidebarProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
  user: { name: string; email: string };
  chats: Chat[];
  activeChatId: string | null;
  onChatSelect: (id: string) => void;
  onNewChat: () => void;
  onDeleteChat: (id: string) => void;
  onLogout: () => void;
  collapsed: boolean;
  onToggle: () => void;
}

const navItems: { tab: Tab; icon: string; label: string }[] = [
  { tab: 'chat', icon: 'MessageSquare', label: 'Чат' },
  { tab: 'history', icon: 'Clock', label: 'История' },
  { tab: 'profile', icon: 'User', label: 'Профиль' },
  { tab: 'settings', icon: 'Shield', label: 'Безопасность' },
];

export default function Sidebar({
  activeTab, onTabChange, user, chats, activeChatId,
  onChatSelect, onNewChat, onDeleteChat, onLogout, collapsed, onToggle
}: SidebarProps) {
  return (
    <aside className={`flex flex-col h-full glass border-r border-white/[0.06] transition-all duration-300 ${collapsed ? 'w-16' : 'w-64'}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/[0.06]">
        {!collapsed && (
          <div>
            <span className="font-display text-lg text-white/90">OxiwisAI</span>
            <div className="text-white/30 text-[9px] tracking-[3px] uppercase">by Oxiwis</div>
          </div>
        )}
        <button
          onClick={onToggle}
          className="w-8 h-8 flex items-center justify-center rounded-lg text-white/40 hover:text-white hover:bg-white/05 transition-all"
        >
          <Icon name={collapsed ? 'PanelLeftOpen' : 'PanelLeftClose'} size={16} />
        </button>
      </div>

      {/* New Chat */}
      <div className="p-3">
        <button
          onClick={() => { onNewChat(); onTabChange('chat'); }}
          className={`btn-ghost w-full rounded-xl transition-all flex items-center gap-2.5 ${collapsed ? 'justify-center p-2.5' : 'px-3 py-2.5'}`}
        >
          <Icon name="Plus" size={16} />
          {!collapsed && <span className="text-sm">Новый чат</span>}
        </button>
      </div>

      {/* Nav */}
      <nav className="px-3 space-y-1">
        {navItems.map(({ tab, icon, label }) => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            className={`w-full flex items-center gap-2.5 rounded-xl transition-all duration-200 text-sm ${collapsed ? 'justify-center p-2.5' : 'px-3 py-2.5'}
              ${activeTab === tab
                ? 'bg-white/08 text-white border border-white/10'
                : 'text-white/40 hover:text-white/80 hover:bg-white/04'
              }`}
          >
            <Icon name={icon} size={16} />
            {!collapsed && <span>{label}</span>}
          </button>
        ))}
      </nav>

      {/* Chat History (only in history view or as sidebar mini-list) */}
      {!collapsed && activeTab === 'history' && chats.length > 0 && (
        <div className="flex-1 overflow-y-auto px-3 mt-3 space-y-1">
          <p className="text-white/25 text-[10px] uppercase tracking-widest px-2 mb-2">Диалоги</p>
          {chats.map((chat) => (
            <div key={chat.id} className="group flex items-center gap-1">
              <button
                onClick={() => { onChatSelect(chat.id); onTabChange('chat'); }}
                className={`flex-1 text-left px-3 py-2 rounded-xl text-xs transition-all truncate ${
                  activeChatId === chat.id ? 'bg-white/08 text-white' : 'text-white/40 hover:text-white/70 hover:bg-white/04'
                }`}
              >
                {chat.title}
              </button>
              <button
                onClick={() => onDeleteChat(chat.id)}
                className="opacity-0 group-hover:opacity-100 w-6 h-6 flex items-center justify-center rounded-lg text-white/30 hover:text-red-400 transition-all"
              >
                <Icon name="Trash2" size={11} />
              </button>
            </div>
          ))}
        </div>
      )}

      {!collapsed && activeTab !== 'history' && chats.length > 0 && (
        <div className="flex-1 overflow-y-auto px-3 mt-3 space-y-1">
          <p className="text-white/25 text-[10px] uppercase tracking-widest px-2 mb-2">Последние</p>
          {chats.slice(0, 5).map((chat) => (
            <button
              key={chat.id}
              onClick={() => { onChatSelect(chat.id); onTabChange('chat'); }}
              className={`w-full text-left px-3 py-2 rounded-xl text-xs transition-all truncate ${
                activeChatId === chat.id ? 'bg-white/08 text-white' : 'text-white/40 hover:text-white/70 hover:bg-white/04'
              }`}
            >
              {chat.title}
            </button>
          ))}
        </div>
      )}

      <div className="flex-1" />

      {/* User + Logout */}
      <div className="p-3 border-t border-white/[0.06]">
        {!collapsed && (
          <div className="glass rounded-xl p-3 mb-2">
            <p className="text-white text-sm font-medium truncate">{user.name}</p>
            <p className="text-white/35 text-xs truncate">{user.email}</p>
          </div>
        )}
        <button
          onClick={onLogout}
          className={`btn-ghost w-full rounded-xl flex items-center gap-2 text-red-400/70 border-red-500/10 hover:text-red-400 hover:border-red-500/20 ${collapsed ? 'justify-center p-2.5' : 'px-3 py-2.5'}`}
        >
          <Icon name="LogOut" size={14} />
          {!collapsed && <span className="text-xs">Выйти</span>}
        </button>
      </div>
    </aside>
  );
}
