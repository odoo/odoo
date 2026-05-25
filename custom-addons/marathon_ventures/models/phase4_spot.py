# -*- coding: utf-8 -*-
"""Phase 4 — Spot Data Mirror credit-adjustment guard (SF Workflow 25).

When a Spot Data Mirror row is credited (Status flipped to 'Credited'),
the SF business rule says the credit reason MUST start with the word
"Network". This module enforces that with an @api.constrains.
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MvSpotDataMirrorPhase4(models.Model):
    _name = 'mv.spot_data_mirror'
    _inherit = ['mv.spot_data_mirror']

    error_reason = fields.Text(
        string='Credit Error Reason',
        help='Required when Status=Credited. MUST start with the word "Network" '
             '(business rule from SF Workflow 25).',
    )

    @api.constrains('status', 'error_reason')
    def _check_credit_reason(self):
        for r in self:
            if r.status == 'credited':
                if not r.error_reason or not r.error_reason.strip().lower().startswith('network'):
                    raise ValidationError(_(
                        "Spot Data Mirror credited rows MUST have a Credit Error Reason "
                        "that starts with the word 'Network'. Got: %s"
                    ) % (r.error_reason or '—'))

    def action_credit_spot(self):
        """Open a wizard to capture the credit reason and flip status to Credited."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Credit Spot — %s') % self.display_name,
            'res_model': 'mv.spot_data_mirror',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
