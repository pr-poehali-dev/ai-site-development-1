
CREATE TABLE t_p59434780_ai_site_development_.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255),
  password_hash VARCHAR(255),
  has_2fa BOOLEAN DEFAULT FALSE,
  tfa_secret VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE t_p59434780_ai_site_development_.email_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL,
  code VARCHAR(6) NOT NULL,
  purpose VARCHAR(50) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  used BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE t_p59434780_ai_site_development_.sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES t_p59434780_ai_site_development_.users(id),
  token VARCHAR(255) UNIQUE NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE t_p59434780_ai_site_development_.chat_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES t_p59434780_ai_site_development_.users(id),
  title VARCHAR(500),
  messages JSONB DEFAULT '[]',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_email_codes_email ON t_p59434780_ai_site_development_.email_codes(email);
CREATE INDEX idx_sessions_token ON t_p59434780_ai_site_development_.sessions(token);
CREATE INDEX idx_sessions_user_id ON t_p59434780_ai_site_development_.sessions(user_id);
CREATE INDEX idx_chat_history_user_id ON t_p59434780_ai_site_development_.chat_history(user_id);
