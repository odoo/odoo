# -*- coding: utf-8 -*-
"""การเชื่อมต่อฐานข้อมูล Odoo 15 (ระบบเดิม) แบบอ่านอย่างเดียว ผ่าน psycopg2

ฐานข้อมูลเดิมจะถูก restore แยกเป็นอีกฐานข้อมูลหนึ่ง (แนะนำชื่อ od15_stage)
จากไฟล์ pg_dump แบบ custom format และห้ามเขียนข้อมูลกลับเข้าไปเด็ดขาด
โมดูลนี้จึงบังคับ session ให้เป็น read-only ทุกครั้งที่เปิดการเชื่อมต่อ

ค่าการเชื่อมต่ออ่านจาก environment variable:
    OD15_HOST, OD15_PORT, OD15_DB, OD15_USER, OD15_PASSWORD
(ค่า host/port/db/user มีค่าเริ่มต้นให้ ถ้าไม่ตั้ง)

หมายเหตุ: คลัสเตอร์ PostgreSQL ของโปรเจกต์นี้มี role เดียวคือ `odoo`
จึงตั้งเป็นค่าเริ่มต้นของ user ส่วนรหัสผ่านไม่เก็บไว้ในโค้ดเลย — ปล่อยให้
libpq หยิบจากไฟล์ .pgpass ของผู้ใช้เอง (ถ้าตั้ง OD15_PASSWORD จะใช้ค่านั้นแทน)
"""
import os
import logging
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

_logger = logging.getLogger('migration.legacy')

# ค่าเริ่มต้นที่สมเหตุสมผลสำหรับ host/port/db/user
# (รหัสผ่านจงใจไม่ใส่ค่าเริ่มต้น — ใช้ .pgpass ของผู้ใช้)
_DEFAULTS = {
    'host': 'localhost',
    'port': '5432',
    'dbname': 'od15_stage',
    'user': 'odoo',
}


def connection_params():
    """ประกอบพารามิเตอร์การเชื่อมต่อจาก environment variable."""
    return {
        'host': os.environ.get('OD15_HOST', _DEFAULTS['host']),
        'port': os.environ.get('OD15_PORT', _DEFAULTS['port']),
        'dbname': os.environ.get('OD15_DB', _DEFAULTS['dbname']),
        'user': os.environ.get('OD15_USER') or _DEFAULTS['user'],
        'password': os.environ.get('OD15_PASSWORD'),
    }


@contextmanager
def legacy_cursor():
    """เปิด cursor แบบอ่านอย่างเดียว (read-only transaction)

    ใช้ conn.set_session(readonly=True) เพื่อรับประกันว่าไม่มีการเขียนเกิดขึ้น
    (เทียบเท่ากับการสั่ง SET TRANSACTION READ ONLY ของ PostgreSQL)
    """
    params = connection_params()
    _logger.info("เชื่อมต่อฐานข้อมูลเดิม: %s@%s:%s/%s",
                 params['user'], params['host'], params['port'], params['dbname'])
    conn = psycopg2.connect(**params)
    try:
        # บังคับ read-only + ไม่ autocommit (อ่านอย่างเดียวเท่านั้น)
        conn.set_session(readonly=True, autocommit=False)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        # ไม่มีการเขียนใด ๆ จึง rollback ทิ้งเสมอ (ปลอดภัยกว่า commit)
        conn.rollback()
    finally:
        conn.close()


def fetch_all(sql, params=None):
    """อ่านข้อมูลหลายแถว คืนค่าเป็น list ของ dict."""
    with legacy_cursor() as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def fetch_one(sql, params=None):
    """อ่านข้อมูลแถวเดียว คืนค่าเป็น dict หรือ None."""
    with legacy_cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None
