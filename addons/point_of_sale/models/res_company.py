# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError

class ResCompany(models.Model):
    _inherit = 'res.company'

    point_of_sale_update_stock_quantities = fields.Selection([
            ('closing', 'At the session closing (advised)'),
            ('real', 'In real time'),
            ], default='closing', string="Update quantities in stock",
            help="At the session closing: A picking is created for the entire session when it's closed\n In real time: Each order sent to the server create its own picking")

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
                    "&",
                    "&",
                    ("company_id", "=", record.id),
                    ("state", "!=", "closed"),
                    "|",
                    ("start_at", "<=", record.period_lock_date),
                    ("start_at", "<=", record.fiscalyear_lock_date),
                ]
            )
            if sessions_in_period:
                sessions_str = ', '.join(sessions_in_period.mapped('name'))
                raise ValidationError(_("Please close all the point of sale sessions in this period before closing it. Open sessions are: %s ") % (sessions_str))
