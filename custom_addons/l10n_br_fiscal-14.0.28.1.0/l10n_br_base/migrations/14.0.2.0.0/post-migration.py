import logging

_logger = logging.getLogger(__name__)
try:
    from openupgradelib import openupgrade
except ImportError:
    openupgrade = None


def migrate(cr, version):
    cr.execute(
        """UPDATE res_partner
        SET street=(street_name||', '||street_number)
        WHERE country_id =(
            SELECT id
            FROM res_country
            WHERE code='BR');
        """
    )
