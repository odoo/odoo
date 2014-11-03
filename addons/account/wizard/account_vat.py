from openerp import models, fields, api, _

class account_vat_declaration(models.TransientModel):
    _name = 'account.vat.declaration'
    _description = 'Account Vat Declaration'
    _inherit = "account.common.report"

    @api.model
    def _get_tax(self):
        tax = self.env['account.tax.code'].search([('parent_id', '=', False), ('company_id', '=', self.env.user.company_id.id)], limit=1)
        return tax

    based_on = fields.Selection([('invoices', 'Invoices'), ('payments', 'Payments'),],
        string='Based on', required=True, default='invoices')
    chart_tax_id = fields.Many2one('account.tax.code', string='Chart of Tax', required=True,
        help='Select Charts of Taxes', domain = [('parent_id','=', False)], default=lambda self: self._get_tax())
    display_detail = fields.Boolean(string='Display Detail')

    @api.multi
    def create_vat(self):
        datas = {
         'ids': self._context.get('active_ids', []),
         'model': 'account.tax.code',
         'form': self.read()[0]
        }

        for field in datas['form'].keys():
            if isinstance(datas['form'][field], tuple):
                datas['form'][field] = datas['form'][field][0]

        taxcode_id = datas['form']['chart_tax_id']
        taxcode = self.env['account.tax.code'].browse(taxcode_id)
        datas['form']['company_id'] = taxcode.company_id.id

        return self.pool['report'].get_action([], 'account.report_vat', data=datas)
