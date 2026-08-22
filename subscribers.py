import os

import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

CATEGORIES = {
    "concerts": "🎵 حفلات موسيقية",
    "sports": "⚽ مباريات وفعاليات رياضية",
    "theaters": "🎭 مسرح وعروض",
    "dining": "🍽️ تجارب طعام",
    "activities": "🎪 أنشطة وفعاليات",
}


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL غير موجود في .env")

    return psycopg.connect(DATABASE_URL)


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    user_id BIGINT PRIMARY KEY,
                    registered_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS subscriber_categories (
                    user_id BIGINT NOT NULL
                        REFERENCES subscribers(user_id)
                        ON DELETE CASCADE,
                    section_key TEXT NOT NULL,
                    PRIMARY KEY (user_id, section_key)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS watched_events (
                    id SERIAL PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    label TEXT,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS event_snapshots (
                    id BIGSERIAL PRIMARY KEY,
                    event_id INTEGER NOT NULL
                        REFERENCES watched_events(id)
                        ON DELETE CASCADE,
                    captured_at TIMESTAMPTZ DEFAULT NOW(),
                    fingerprint TEXT NOT NULL,
                    data JSONB NOT NULL
                )
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_snapshots_event
                ON event_snapshots(event_id, captured_at DESC)
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS guest_requests (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT,
                    guest_name TEXT,
                    hotel TEXT,
                    event_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    category TEXT,
                    status TEXT DEFAULT 'new',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)


def add_subscriber(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO subscribers (user_id)
                VALUES (%s)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id,))


def get_user_categories(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT section_key
                FROM subscriber_categories
                WHERE user_id = %s
            """, (user_id,))

            return [row[0] for row in cur.fetchall()]


def toggle_category(user_id, section_key):
    if section_key not in CATEGORIES:
        return

    add_subscriber(user_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1
                FROM subscriber_categories
                WHERE user_id = %s
                  AND section_key = %s
            """, (user_id, section_key))

            if cur.fetchone():
                cur.execute("""
                    DELETE FROM subscriber_categories
                    WHERE user_id = %s
                      AND section_key = %s
                """, (user_id, section_key))
            else:
                cur.execute("""
                    INSERT INTO subscriber_categories
                    (user_id, section_key)
                    VALUES (%s, %s)
                """, (user_id, section_key))


def add_watch(url, label=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO watched_events (url, label)
                VALUES (%s, %s)
                ON CONFLICT (url)
                DO UPDATE SET
                    active = TRUE,
                    label = COALESCE(
                        EXCLUDED.label,
                        watched_events.label
                    )
                RETURNING id
            """, (url, label))

            return cur.fetchone()[0]


def list_watches():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, url, label
                FROM watched_events
                WHERE active = TRUE
                ORDER BY id
            """)

            return cur.fetchall()


def get_last_snapshot(event_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT fingerprint, data
                FROM event_snapshots
                WHERE event_id = %s
                ORDER BY captured_at DESC
                LIMIT 1
            """, (event_id,))

            row = cur.fetchone()

            if not row:
                return None

            return {
                "fingerprint": row[0],
                "data": row[1],
            }


def save_snapshot(event_id, fingerprint, data):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO event_snapshots
                (event_id, fingerprint, data)
                VALUES (%s, %s, %s)
            """, (
                event_id,
                fingerprint,
                Jsonb(data),
            ))


def add_guest_request(
    user_id,
    guest_name,
    hotel,
    event_name,
    quantity,
    category
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO guest_requests
                (
                    user_id,
                    guest_name,
                    hotel,
                    event_name,
                    quantity,
                    category
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                guest_name,
                hotel,
                event_name,
                quantity,
                category,
            ))

            return cur.fetchone()[0]


def list_guest_requests(limit=20):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    guest_name,
                    hotel,
                    event_name,
                    quantity,
                    category,
                    status,
                    created_at
                FROM guest_requests
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))

            return cur.fetchall()


init_db()