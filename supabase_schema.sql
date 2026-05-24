create table if not exists public.scenarios (
    id uuid default gen_random_uuid() primary key,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    user_id text,
    user_email text,
    name text,
    scenario_name text,
    payload jsonb,
    data jsonb
);

alter table public.scenarios disable row level security;
