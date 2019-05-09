# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.osv import expression
from odoo.addons.account.models import reconciliation_widget

old_method = reconciliation_widget.AccountReconciliation._domain_move_lines_for_reconciliation


class AccountReconciliation(models.AbstractModel):

    _inherit = 'account.reconciliation.widget'

    @api.model
    def _domain_move_lines_for_reconciliation(
        self, st_line, aml_accounts, partner_id, excluded_ids=None,
        search_str=False):
        """ Allow to search by display_name on bank statements and partner
        debt reconcile
        """
        _super = super(AccountReconciliation, self)
        _get_domain = _super._domain_move_lines_for_reconciliation
        domain = _get_domain(
            self, st_line, aml_accounts, partner_id, excluded_ids=excluded_ids,
            search_str=search_str)
        if not str and str != '/':
            return domain
        domain_trans_ref = [('move_id.display_name', 'ilike', str)]
        return expression.OR([domain, domain_trans_ref])
