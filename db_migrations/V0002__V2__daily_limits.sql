CREATE TABLE t_p59434780_ai_site_development_.daily_limits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES t_p59434780_ai_site_development_.users(id),
  day DATE NOT NULL,
  requests_count INTEGER DEFAULT 1,
  UNIQUE(user_id, day)
);

CREATE INDEX idx_daily_limits_user_day ON t_p59434780_ai_site_development_.daily_limits(user_id, day);
