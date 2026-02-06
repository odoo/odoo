# Part of GPCB. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PayrollSendWizard(models.TransientModel):
    _name = 'l10n_co.payroll.send.wizard'
    _description = 'Batch Send Payroll Documents to DIAN'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
    )
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)

    def action_send(self):
        """Batch send all confirmed payroll documents for the period."""
        self.ensure_one()

        documents = self.env['l10n_co.payroll.document'].search([
            ('company_id', '=', self.company_id.id),
            ('period_start', '>=', self.period_start),
            ('period_end', '<=', self.period_end),
            ('state', '=', 'confirmed'),
        ])

        if not documents:
            raise UserError(_(
                'No confirmed payroll documents found for the selected period.'
            ))

        success_count = 0
        error_count = 0
        errors = []

        for doc in documents:
            try:
                doc.action_send_to_dian()
                if doc.state in ('sent', 'validated'):
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f'{doc.document_number}: {doc.dian_response or "Unknown error"}')
            except Exception as e:
                error_count += 1
                errors.append(f'{doc.document_number}: {str(e)}')

        message = _(
            'Batch submission complete: %d sent, %d errors.',
            success_count, error_count,
        )
        if errors:
            message += '\n\n' + '\n'.join(errors[:20])

        return {
            'type': 'ir.actions.act_window',
            'name': _('Submission Results'),
            'res_model': 'l10n_co.payroll.document',
            'domain': [('id', 'in', documents.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }
