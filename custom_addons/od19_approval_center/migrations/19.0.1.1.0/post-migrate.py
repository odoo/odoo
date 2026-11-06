import logging

_logger = logging.getLogger(__name__)

SOURCE_NAME = "ค่าใช้จ่าย (Expense)"


def migrate(cr, version):
    """สลับ source ของ hr.expense จาก field-based เป็น tier_validation."""
    if not version:
        return
    cr.execute(
        """
        SELECT s.id
          FROM od19_approval_source s
          JOIN ir_model m ON m.id = s.model_id
         WHERE m.model = 'hr.expense' AND s.name = %s
         LIMIT 1
        """,
        (SOURCE_NAME,),
    )
    row = cr.fetchone()
    if not row:
        _logger.info("Approval Center: hr.expense source not found, skip")
        return
    source_id = row[0]
    cr.execute(
        "UPDATE od19_approval_source SET strategy = 'tier_validation' WHERE id = %s",
        (source_id,),
    )
    cr.execute("DELETE FROM od19_approval_step WHERE source_id = %s", (source_id,))
    _logger.info(
        "Approval Center: hr.expense source %s switched to tier_validation",
        source_id,
    )
