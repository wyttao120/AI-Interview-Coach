-- AI 面试复盘助手 - 数据库初始化脚本
create table interviews (
  id bigint primary key generated always as identity,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  user_id text not null,
  avg_wpm float8,
  scores jsonb,
  report text,
  transcript text
);