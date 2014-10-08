from openerp import models, fields


class AccountReportsConfiguratorSalePurchaseJournal(models.TransientModel):
    _name = 'configurator.salepurchasejournal'
    _inherit = 'configurator.printjournal'

    def _get_journals(self):
        return self.env['account.journal'].search_read(
            domain=[('type', 'in', ('sale', 'purchase', 'sale_refund', 'purchase_refund'))], fields=['name']
        )

    def _get_default_journals(self):
        return self.env['account.journal'].search([('type', 'in', ('sale', 'purchase', 'sale_refund', 'purchase_refund'))])

    journal_ids = fields.Many2many('account.journal', default=_get_default_journals)
