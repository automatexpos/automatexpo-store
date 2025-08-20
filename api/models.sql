create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique not null,
  phone text,
  address text,
  role text default 'customer' check (role in ('customer','admin')),
  created_at timestamp with time zone default now()
);

alter table public.profiles enable row level security;

create policy "Public can insert own profile" on public.profiles
  for insert with check (auth.uid() = id);

create policy "Users can select/update own profile" on public.profiles
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- 2) phones inventory
create table if not exists public.phones (
  id bigserial primary key,
  model text not null,
  specs text,
  condition text,
  price numeric(12,2) not null,
  status text not null default 'Available' check (status in ('Available','Booked','Sold')),
  payment_status text, -- e.g. 'Verification pending', 'Paid full', 'Token paid'
  full_payment boolean default false,
  shipping_status text default 'Pending', -- 'Pending','Shipped'
  buyer_email text,
  buyer_phone text,
  booking_time timestamp with time zone,
  selling_time timestamp with time zone,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

alter table public.phones enable row level security;

create policy "Anyone can read phones" on public.phones for select using (true);

-- 3) phone media (Cloudinary URLs)
create table if not exists public.phone_media (
  id bigserial primary key,
  phone_id bigint references public.phones(id) on delete cascade,
  url text not null,
  kind text default 'image' check (kind in ('image','video')),
  created_at timestamp with time zone default now()
);

alter table public.phone_media enable row level security;
create policy "Anyone can read media" on public.phone_media for select using (true);