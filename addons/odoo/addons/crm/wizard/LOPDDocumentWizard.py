from odoo import models, fields, api, _

class LOPDDocumentWizard(models.TransientModel):
    _name = 'lopd.document.wizard'
    _description = 'Asistente para importar documento LOPD'

    partner_id = fields.Many2one('res.partner', string='Contacto', required=True)
    document_type = fields.Selection(
        [('lopd', 'LOPD'), ('sepa', 'SEPA')],
        string='Tipo de documento',
        required=True,
        default='lopd',
    )
    name = fields.Char(string='Nombre del documento', required=True, default='LOPD_Firmada')
    datas = fields.Binary(string='Archivo', required=True)
    filename = fields.Char(string='Nombre del archivo')

    def action_import_document(self):
        self.ensure_one()

        attachment = self.env['ir.attachment'].create({
            'name': self.name,
            'datas': self.datas,
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'type': 'binary',
        })

        target_field = 'lopd_document_id' if self.document_type == 'lopd' else 'billing_sepa_document_id'
        self.partner_id.write({
            target_field: attachment.id,
        })

        return {'type': 'ir.actions.act_window_close'}