# api/supa.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load .env file if present (only affects local dev; Vercel ignores it)
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# For admin password reset flow we need service role
admin_client: Client | None = None
if SUPABASE_SERVICE_ROLE_KEY:
    admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
