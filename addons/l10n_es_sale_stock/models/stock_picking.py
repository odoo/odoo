# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_es_tractor_license_plate = fields.Char(string="Main vehicle or tractor licence plate")
    l10n_es_trailer_license_plate = fields.Char(string="Trailer or semi-trailer licence plate")
    l10n_es_authorization_observation = fields.Text(string="Authorisations and observations")
    l10n_es_sender_contact_id = fields.Many2one(
        comodel_name='res.partner',
        string="Sender contact",
        help="Sender contact whose details are printed in box 1 of the DeCA (leave in blank if it's your company)",
    )
    l10n_es_carrier_contact_id = fields.Many2one(
        comodel_name='res.partner',
        string="Contractual carrier contact",
        help="Contractual carrier contact whose details are printed in box 3 of the DeCA (leave in blank if it's your company)",
    )

    # Every DeCA an attachment linked with One2many to picking to show a history
    l10n_es_deca_attachment_ids = fields.One2many(
        comodel_name='ir.attachment',
        inverse_name='l10n_es_deca_picking_id',
        string="DeCA versions",
    )

    def action_l10n_es_print_deca(self):
        pickings = self.filtered(lambda p: p.picking_type_code == 'outgoing')
        if not pickings:
            raise UserError(self.env._("The DeCA can only be printed for deliveries."))

        attachments = self.env['ir.attachment'].create([{
            'name': f'DeCA - {picking.name} - v{len(picking.l10n_es_deca_attachment_ids) + 1}',
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'l10n_es_deca_picking_id': picking.id,
        } for picking in pickings])

        for picking, attachment in zip(pickings, attachments):
            # Access token creates an array so we retrieve first position
            access_token = attachment.generate_access_token()[0]
            deca_url = f'{picking.get_base_url()}/web/content/{attachment.id}?access_token={access_token}&download=true'

            # Template calls deca_url retrieved from data dict
            pdf_content, _content_type = self.env['ir.actions.report']._render_qweb_pdf(
                'l10n_es_sale_stock.report_deca', picking.id, data={'deca_url': deca_url},
            )

            attachment.raw = pdf_content

        if len(attachments) == 1:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachments.id}?download=true',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("DeCA"),
            'res_model': 'ir.attachment',
            'view_mode': 'list',
            'views': [(self.env.ref('l10n_es_sale_stock.view_ir_attachment_deca_list').id, 'list')],
            'domain': [('id', 'in', attachments.ids)],
        }
