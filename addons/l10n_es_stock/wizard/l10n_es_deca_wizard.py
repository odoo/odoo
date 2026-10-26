# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields, models


class L10nEsDecaWizard(models.TransientModel):
    _name = 'l10n_es.deca.wizard'
    _description = 'DeCA Generate Wizard'

    picking_ids = fields.Many2many('stock.picking', string="Deliveries", required=True)
    tractor_license_plate = fields.Char(string="Main vehicle or tractor license plate")
    trailer_license_plate = fields.Char(string="Trailer or semi-trailer license plate")
    authorization_observation = fields.Text(string="Authorisations and observations")
    sender_id = fields.Many2one(
        comodel_name='res.partner',
        string="Sender contact",
        help="Sender contact whose details are printed in box 1 of the DeCA (leave blank if it's your company)",
    )
    carrier_id = fields.Many2one(
        comodel_name='res.partner',
        string="Contractual carrier contact",
        help="Contractual carrier contact whose details are printed in box 3 of the DeCA (leave blank if it's your company)",
    )

    def action_generate_deca(self):
        self.ensure_one()
        pickings = self.picking_ids
        attachment_name = "DeCA - " + pickings[0].name + " -- " + pickings[-1].name if len(pickings) > 1 else "DeCA - " + pickings[0].name

        attachment = self.env['ir.attachment'].create({
            'name': attachment_name,
            'res_model': 'stock.picking',
            'res_id': pickings[0].id,
        })
        pickings.l10n_es_deca_attachment_ids = [Command.link(attachment.id)]

        # Access token creates an array so we retrieve first position
        access_token = attachment.generate_access_token()[0]
        deca_url = f'{self.get_base_url()}/web/content/{attachment.id}?access_token={access_token}&download=true'

        report_data = {
            'deca_url': deca_url,
            'tractor_license_plate': self.tractor_license_plate,
            'trailer_license_plate': self.trailer_license_plate,
            'authorization_observation': self.authorization_observation,
            'sender_contact_id': self.sender_id,
            'carrier_contact_id': self.carrier_id,
        }
        pdf_content, _content_type = self.env['ir.actions.report']._render_qweb_pdf(
            'l10n_es_stock.report_deca', pickings.ids, data=report_data,
        )
        attachment.raw = pdf_content

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'close': True,
        }
