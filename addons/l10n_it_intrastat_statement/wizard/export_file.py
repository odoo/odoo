

from openerp import models, api, fields
import base64
import contextlib

from openerp import tools
from openerp.tools.translate import _
from openerp.tools.misc import get_iso_codes

class account_intrastat_export_file(models.TransientModel):
    _name = "account.intrastat.export.file"
    
    name = fields.Char(string='File Name', readonly=True)
    data = fields.Binary(string='File', readonly=True)
    state = fields.Selection([('choose', 'choose'), 
                              ('get', 'get')], 
                             string='State', default='choose')

    @api.multi
    def act_getfile(self):
        statement_id = self.env.context.get('active_id')
        statement = self.env['account.intrastat.statement'].browse(statement_id)
        file = statement.generate_file_export()
        filename = statement._get_file_name()
        out = base64.encodestring(file)

        view = self.env['ir.model.data'].get_object_reference(
            'l10n_it_intrastat_statement', 
            'wizard_account_intrastat_export_file')
        view_id = view[1] or False

        self.write({ 'state': 'get', 'data': out, 'name': filename })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.intrastat.export.file',
            'view_mode': 'form',
            'view_type': 'form',
            'name': _('Export Intrastat File'),
            'res_id': self.id,
            'nodestroy': True,
            'view_id': [view_id],
            'target': 'new',
        }
