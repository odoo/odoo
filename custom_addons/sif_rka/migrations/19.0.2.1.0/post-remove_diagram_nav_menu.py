import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    menu = env.ref("sif_rka.menu_sif_rka_diagram", raise_if_not_found=False)
    if menu and menu.exists():
        menu.unlink()
        _logger.info("Removed duplicate Diagram Anggaran navbar menu.")
