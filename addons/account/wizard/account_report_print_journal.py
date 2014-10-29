from openerp import models, fields, api, _
from lxml import etree


class account_print_journal(models.TransientModel):
    _inherit = "account.common.journal.report"
    _name = 'account.print.journal'
    _description = 'Account Print Journal'

    sort_selection = fields.Selection([('l.date', 'Date'), ('am.name', 'Journal Entry Number'),],
        string='Entries Sorted by', required=True, default='am.name')
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        '''
        used to set the domain on 'journal_ids' field: we exclude or only propose the journals of type 
        sale/purchase (+refund) accordingly to the presence of the key 'sale_purchase_only' in the context.
        '''
        res = super(account_print_journal, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])

        if self._context.get('sale_purchase_only'):
            domain ="[('type', 'in', ('sale','purchase','sale_refund','purchase_refund'))]"
        else:
            domain ="[('type', 'not in', ('sale','purchase','sale_refund','purchase_refund'))]"
        nodes = doc.xpath("//field[@name='journal_ids']")
        for node in nodes:
            node.set('domain', domain)
        res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['sort_selection'])[0])
        if self._context.get('sale_purchase_only'):
            return self.env['report'].get_action([], 'account.report_salepurchasejournal', data=data)
        else:
            return self.env['report'].get_action([], 'account.report_journal', data=data)
