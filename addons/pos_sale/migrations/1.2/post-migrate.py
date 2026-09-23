import logging

from odoo.addons.base.models.ir_access_convert import rewrite_converted_domain

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    # the rule gave POS managers every crm.team, which held sales teams only;
    # on team.team the same domain would reach every application's teams
    rewrite_converted_domain(
        cr,
        "pos_sale",
        "pos_sale_rule_pos_channel_pos_manager",
        "[('use_sale', '=', True)]",
        logger=_logger,
    )
