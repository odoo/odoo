from odoo import models, fields, api, _

class LOPDDocumentWizard(models.TransientModel):
    _name = 'lopd.document.wizard'
    _description = 'Asistente para importar documento LOPD'

    partner_id = fields.Many2one('res.partner', string='Contacto', required=True)
    name = fields.Char(string='Nombre del documento', required=True, default='LOPD_Firmada')
    datas = fields.Binary(string='Archivo', required=True)
    filename = fields.Char(string='Nombre del archivo')

    def action_import_document(self):
        """Importa el documento y lo vincula al partner"""
        self.ensure_one()
        
        # Crear el adjunto
        attachment = self.env['ir.attachment'].create({
            'name': self.name,
            'datas': self.datas,
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'type': 'binary',
        })
        
        # Actualizar el partner con el documento
        self.partner_id.write({
            'lopd_document_id': attachment.id,
        })
        
        return {'type': 'ir.actions.act_window_close'}