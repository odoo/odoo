# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Reactivate the reverse charge child taxes 9% TXRC-TS and 9% TXRC-ESS.

    They were shipped inactive while their sibling children (TXRC-N33, TXRC-RE)
    were active, so the group taxes referencing them dropped the inactive child
    and computed a wrong GST amount.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'sg')]):
        for xmlid in ('sg_purchase_tax_txrc_ts_9', 'sg_purchase_tax_txrc_ess_9'):
            tax = env.ref(f'account.{company.id}_{xmlid}', raise_if_not_found=False)
            if tax and not tax.active:
                tax.active = True
