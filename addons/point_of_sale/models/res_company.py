# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError

class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = ['res.company', 'pos.load.mixin']

    point_of_sale_update_stock_quantities = fields.Selection([
            ('closing', 'At the session closing (faster)'),
            ('real', 'In real time (accurate but slower)'),
            ], default='closing', string="Update quantities in stock",
            help="At the session closing: A picking is created for the entire session when it's closed\n In real time: Each order sent to the server create its own picking")
    point_of_sale_use_ticket_qr_code = fields.Boolean(
        string='Self-service invoicing',
        help="Print information on the receipt to allow the costumer to easily request the invoice anytime, from Odoo's portal")
    point_of_sale_ticket_unique_code = fields.Boolean(
        string='Generate a code on ticket',
        help="Add a 5-digit code on the receipt to allow the user to request the invoice for an order on the portal.")
    point_of_sale_ticket_portal_url_display_mode = fields.Selection([
            ('qr_code', 'QR code'),
            ('url', 'URL'),
            ('qr_code_and_url', 'QR code + URL'),
        ], default='qr_code',
        string='Print',
        help="Choose how the URL to the portal will be print on the receipt.",
        required=True)

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', '=', data['pos.config']['data'][0]['company_id'])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            'id', 'currency_id', 'email', 'website', 'company_registry', 'vat', 'name', 'phone', 'partner_id',
            'country_id', 'state_id', 'tax_calculation_rounding_method', 'nomenclature_id', 'point_of_sale_use_ticket_qr_code',
            'point_of_sale_ticket_unique_code', 'point_of_sale_ticket_portal_url_display_mode', 'street', 'city', 'zip',
        ]

    @api.constrains('period_lock_date', 'fiscalyear_lock_date')
    def validate_period_lock_date(self):
        """ This constrains makes it impossible to change the period lock date if
        some open POS session exists into it. Without that, these POS sessions
        would trigger an error message saying that the period has been locked when
        trying to close them.
        """
        pos_session_model = self.env['pos.session'].sudo()
        for record in self:
            sessions_in_period = pos_session_model.search(
                [
                    ("company_id", "child_of", record.id),
                    ("state", "!=", "closed"),
                    ("start_at", "<=", record._get_user_fiscal_lock_date()),
                ]
            )
            if sessions_in_period:
                sessions_str = ', '.join(sessions_in_period.mapped('name'))
                raise ValidationError(_("Please close all the point of sale sessions in this period before closing it. Open sessions are: %s ", sessions_str))
