create table conversations (
  id bigint primary key generated always as identity,
  claim_id text,
  claim_date date,
  claim_status text,
  claim_amount numeric,
  created_at timestamptz default now()
);