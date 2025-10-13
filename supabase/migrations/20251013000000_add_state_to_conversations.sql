alter table conversations add column state text default 'initial' check (state in ('initial', 'ongoing', 'done'));

