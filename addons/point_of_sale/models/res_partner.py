# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    pos_order_count = fields.Integer(
        compute='_compute_pos_order',
        help="The number of point of sales orders related to this customer",
        groups="point_of_sale.group_pos_user",
    )
    pos_order_ids = fields.One2many('pos.order', 'partner_id', readonly=True)
    barcode = fields.Char(help="Use a barcode to identify this contact from the Point of Sale.", copy=False)

    _sql_constraints = [
        ('unique_barcode', 'unique(barcode, company_id)', 'This barcode is already assigned to another contact. Please make sure you assign a unique barcode to this contact.'),
    ]

    def _compute_pos_order(self):
        partners_data = self.env['pos.order'].read_group([('partner_id', 'in', self.ids)], ['partner_id'], ['partner_id'])
        mapped_data = dict([(partner['partner_id'][0], partner['partner_id_count']) for partner in partners_data])
        for partner in self:
            partner.pos_order_count = mapped_data.get(partner.id, 0)

    @api.model
    def create_from_ui(self, partner):
        """ create or modify a partner from the point of sale ui.
            partner contains the partner's fields. """
        # image is a dataurl, get the data after the comma
        if partner.get('image_1920'):
            partner['image_1920'] = partner['image_1920'].split(',')[1]
        partner_id = partner.pop('id', False)
        if partner_id:  # Modifying existing partner
            self.browse(partner_id).write(partner)
        else:
            partner['lang'] = self.env.user.lang
            partner_id = self.create(partner).id
        return partner_id

    def unlink(self):
        running_sessions = self.env['pos.session'].search([('state', '!=', 'closed')])
        if running_sessions:
            raise UserError(
                _("You cannot delete contacts while there are active PoS sessions. Close the session(s) %s first.")
                % ", ".join(session.name for session in running_sessions)
            )
        return super(ResPartner, self).unlink()
