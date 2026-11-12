# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import logging

_logger = logging.getLogger(__name__)


def pre_init_hook(env):
    """สร้าง extension pg_trgm ก่อนติดตั้ง เพื่อให้ดัชนี GIN trigram สร้างได้"""
    env.cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    _logger.info("od19_document_hub: pg_trgm extension พร้อมใช้งาน")
