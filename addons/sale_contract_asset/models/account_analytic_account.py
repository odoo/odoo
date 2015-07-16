from openerp import models, fields, api


class account_analytic_account(models.Model):
    _name = "account.analytic.account"
    _inherit = "account.analytic.account"

    asset_category_id = fields.Many2one('account.asset.category', 'Deferred Revenue Category',
                                        help="This asset category will be applied to the lines of the contract's invoices.",
                                        domain="[('type','=','sale')]")

    @api.multi
    def on_change_template(self, template_id, date_start=False):
        res = super(account_analytic_account, self).on_change_template(template_id, date_start)

        template = self.browse(template_id)
        if template.asset_category_id:
            res['value']['asset_category_id'] = template.asset_category_id.id

        return res

    @api.model
    def _prepare_invoice_lines(self, contract, fiscal_position_id):
        inv_lines = super(account_analytic_account, self)._prepare_invoice_lines(contract, fiscal_position_id)

        for line in inv_lines:
            line[2]['asset_category_id'] = contract.asset_category_id and contract.asset_category_id.id

        return inv_lines
