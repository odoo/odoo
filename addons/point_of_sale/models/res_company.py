# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from odoo.osv import expression

class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = ['res.company', 'pos.load.mixin']

    point_of_sale_update_stock_quantities = fields.Selection([
            ('closing', 'At the session closing'),
            ('real', 'In real time'),
            ], default='real', string="Update quantities in stock",
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
            'account_fiscal_country_id',
        ]

    @api.constrains('fiscalyear_lock_date', 'tax_lock_date', 'sale_lock_date', 'hard_lock_date')
    def validate_lock_dates(self):
        """ This constrains makes it impossible to change the relevant lock dates if
        some open POS session would violate them. Without that, these POS sessions
        could not be closed (since the closing entries violate the lock dates).
        """
        pos_session_model = self.env['pos.session'].sudo()
        for record in self:
            record = record.with_context(ignore_exceptions=True)
            fiscal_lock_date = max(record.user_fiscalyear_lock_date, record.user_hard_lock_date)
            sessions_in_period = pos_session_model.search(
                [
                    ("company_id", "child_of", record.id),
                    ("state", "!=", "closed"),
                    *expression.OR([
                        [("start_at", "<=", fiscal_lock_date)],
                        [("start_at", "<=", record.user_tax_lock_date)],
                        # The `config_id.journal_id.type` is either 'sale' or 'misc'
                        [("config_id.journal_id.type", "=", 'sale'),
                         ("start_at", "<=", record.user_sale_lock_date)],
                    ])
                ]
            )
            if sessions_in_period:
                sessions_str = ', '.join(sessions_in_period.mapped('name'))
                raise ValidationError(_("Please close all the point of sale sessions in this period before closing it. Open sessions are: %s ", sessions_str))
