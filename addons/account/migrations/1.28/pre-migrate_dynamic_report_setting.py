import logging

from lxml import etree
from psycopg.types.json import Json

from odoo.db.schema import table_exists

_logger = logging.getLogger(__name__)

# ea6ec9d4d3e0 removed the "Dynamic Reports" upsell setting from account's
# settings view and the two <setting id="dynamic_report" position="attributes">
# overrides its children carried. An upgrade writes the parent before those
# children are reloaded from XML, and writing a parent validates its stored
# children, which still xpath onto the setting: `-u` stopped at module account
# on every database that had the old views. The stale nodes go before load.


def migrate(cr, version):
    if not version or not table_exists(cr, "ir_ui_view"):
        return
    cr.execute(
        """
        SELECT id, arch_db FROM ir_ui_view
         WHERE model = 'res.config.settings'
           AND arch_db::text LIKE %s
        """,
        ("%dynamic_report%",),
    )
    for view_id, arch in cr.fetchall():
        rewritten = {}
        for lang, value in (arch or {}).items():
            root = etree.fromstring(value.encode())
            stale = root.xpath("//*[@id='dynamic_report']")
            for node in stale:
                node.getparent().remove(node)
            rewritten[lang] = (
                etree.tostring(root, encoding="unicode") if stale else value
            )
        if rewritten != (arch or {}):
            cr.execute(
                "UPDATE ir_ui_view SET arch_db = %s WHERE id = %s",
                (Json(rewritten), view_id),
            )
            _logger.info(
                "account 1.28: view %s no longer overrides the retired "
                "dynamic_report setting",
                view_id,
            )
