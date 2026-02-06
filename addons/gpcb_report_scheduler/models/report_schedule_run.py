# Part of GPCB. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ReportScheduleRun(models.Model):
    _name = 'gpcb.report.schedule.run'
    _description = 'Report Schedule Execution'
    _order = 'create_date desc'

    schedule_id = fields.Many2one(
        'gpcb.report.schedule', required=True, ondelete='cascade',
    )
    report_type = fields.Selection(
        related='schedule_id.report_type', store=True, readonly=True,
    )
    date_from = fields.Date(string='Period Start', required=True)
    date_to = fields.Date(string='Period End', required=True)
    state = fields.Selection(
        selection=[
            ('generated', 'Generated'),
            ('review', 'Pending Review'),
            ('approved', 'Approved'),
            ('sent', 'Sent'),
            ('failed', 'Failed'),
        ],
        string='Status', default='generated', required=True,
    )
    report_data = fields.Text(
        string='Report Data (JSON)',
        help='Frozen snapshot of the report data at generation time.',
    )
    pdf_file = fields.Binary(string='PDF Report')
    pdf_filename = fields.Char(string='PDF Filename')
    notes = fields.Text(string='Review Notes')
    error_message = fields.Text(string='Error')
    sent_date = fields.Datetime(string='Sent Date')

    def _generate_report_content(self):
        """Generate the report content as a data snapshot.

        Queries account.move data for the period and stores a JSON summary.
        """
        self.ensure_one()
        try:
            company = self.schedule_id.company_id
            date_from = self.date_from
            date_to = self.date_to

            Move = self.env['account.move'].sudo()

            if self.report_type in ('iva_300', 'withholding_350'):
                data = self._generate_tax_report_data(Move, company, date_from, date_to)
            elif self.report_type == 'withholding_cert':
                data = self._generate_withholding_cert_summary(Move, company, date_from, date_to)
            elif self.report_type == 'exogenous':
                data = self._generate_exogenous_summary(company, date_from, date_to)
            elif self.report_type in ('balance_sheet', 'profit_loss', 'trial_balance'):
                data = self._generate_financial_report_data(Move, company, date_from, date_to)
            else:
                data = self._generate_generic_summary(Move, company, date_from, date_to)

            self.report_data = json.dumps(data, default=str, indent=2)
            self.state = 'generated'

            # Generate a simple filename
            self.pdf_filename = (
                f"{self.report_type}_{date_from.isoformat()}_{date_to.isoformat()}.json"
            )

            _logger.info(
                'Report generated: %s for %s to %s',
                self.report_type, date_from, date_to,
            )

        except Exception as e:
            _logger.exception('Report generation failed')
            self.state = 'failed'
            self.error_message = str(e)

    def _generate_tax_report_data(self, Move, company, date_from, date_to):
        """Generate IVA/withholding tax report data."""
        # Sales
        sales = Move.search([
            ('company_id', '=', company.id),
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ])
        # Purchases
        purchases = Move.search([
            ('company_id', '=', company.id),
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ])

        return {
            'report_type': self.report_type,
            'period': {'from': str(date_from), 'to': str(date_to)},
            'company': company.name,
            'sales': {
                'count': len(sales),
                'base_amount': sum(sales.mapped('amount_untaxed')),
                'tax_amount': sum(sales.mapped('amount_tax')),
                'total': sum(sales.mapped('amount_total')),
            },
            'purchases': {
                'count': len(purchases),
                'base_amount': sum(purchases.mapped('amount_untaxed')),
                'tax_amount': sum(purchases.mapped('amount_tax')),
                'total': sum(purchases.mapped('amount_total')),
            },
            'iva_payable': (
                sum(sales.mapped('amount_tax')) - sum(purchases.mapped('amount_tax'))
            ),
        }

    def _generate_withholding_cert_summary(self, Move, company, date_from, date_to):
        """Generate withholding certificate summary data."""
        wh_lines = self.env['account.move.line'].sudo().search([
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('tax_line_id', '!=', False),
        ])

        rtefte_lines = wh_lines.filtered(
            lambda l: (l.tax_line_id.tax_group_id.name or '').upper().startswith(('R REN', 'RTEFTE'))
        )
        rteiva_lines = wh_lines.filtered(
            lambda l: (l.tax_line_id.tax_group_id.name or '').upper().startswith(('R IVA', 'RTEIVA'))
        )
        rteica_lines = wh_lines.filtered(
            lambda l: (l.tax_line_id.tax_group_id.name or '').upper().startswith(('R ICA', 'RTEICA'))
        )

        return {
            'report_type': 'withholding_cert',
            'period': {'from': str(date_from), 'to': str(date_to)},
            'company': company.name,
            'rtefte': {
                'count': len(set(rtefte_lines.mapped('partner_id.id'))),
                'total': sum(abs(l.balance) for l in rtefte_lines),
            },
            'rteiva': {
                'count': len(set(rteiva_lines.mapped('partner_id.id'))),
                'total': sum(abs(l.balance) for l in rteiva_lines),
            },
            'rteica': {
                'count': len(set(rteica_lines.mapped('partner_id.id'))),
                'total': sum(abs(l.balance) for l in rteica_lines),
            },
        }

    def _generate_exogenous_summary(self, company, date_from, date_to):
        """Generate exogenous information summary."""
        ExoDoc = self.env['l10n_co_edi.exogenous.document'].sudo()
        year = date_from.year
        docs = ExoDoc.search([
            ('company_id', '=', company.id),
            ('year', '=', year),
        ])
        return {
            'report_type': 'exogenous',
            'period': {'from': str(date_from), 'to': str(date_to)},
            'company': company.name,
            'year': year,
            'documents': [
                {
                    'formato': d.formato,
                    'state': d.state,
                    'line_count': d.line_count,
                }
                for d in docs
            ],
        }

    def _generate_financial_report_data(self, Move, company, date_from, date_to):
        """Generate balance sheet / P&L / trial balance summary."""
        moves = Move.search([
            ('company_id', '=', company.id),
            ('state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ])

        lines = self.env['account.move.line'].sudo().search([
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ])

        income_lines = lines.filtered(
            lambda l: l.account_id.account_type in ('income', 'income_other')
        )
        expense_lines = lines.filtered(
            lambda l: l.account_id.account_type in ('expense', 'expense_direct_cost', 'expense_depreciation')
        )

        total_income = sum(abs(l.credit - l.debit) for l in income_lines)
        total_expense = sum(abs(l.debit - l.credit) for l in expense_lines)

        return {
            'report_type': self.report_type,
            'period': {'from': str(date_from), 'to': str(date_to)},
            'company': company.name,
            'move_count': len(moves),
            'total_income': total_income,
            'total_expense': total_expense,
            'net_income': total_income - total_expense,
        }

    def _generate_generic_summary(self, Move, company, date_from, date_to):
        """Fallback generic report data."""
        return {
            'report_type': self.report_type,
            'period': {'from': str(date_from), 'to': str(date_to)},
            'company': company.name,
            'note': 'Detailed report generation not yet implemented for this type.',
        }

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_approve(self):
        """Approve the report after review."""
        self.ensure_one()
        if self.state not in ('generated', 'review'):
            raise UserError(_('Only generated or in-review reports can be approved.'))
        self.state = 'approved'

    def action_send(self):
        """Send the report to recipients."""
        self.ensure_one()
        self._send_to_recipients()

    def _send_to_recipients(self):
        """Send the report data to configured recipients via email."""
        self.ensure_one()
        schedule = self.schedule_id
        if not schedule.recipient_ids:
            _logger.info('No recipients configured for schedule %s', schedule.name)
            return

        # Build email
        subject = _(
            '%(report)s — %(from)s to %(to)s',
            report=schedule.name,
            **{'from': self.date_from.isoformat(), 'to': self.date_to.isoformat()},
        )

        body_lines = [
            f'<p><strong>{schedule.name}</strong></p>',
            f'<p>Period: {self.date_from} to {self.date_to}</p>',
            f'<p>Status: {self.state}</p>',
        ]

        if self.report_data:
            body_lines.append('<p>Report data snapshot is attached.</p>')

        body = ''.join(body_lines)

        # Create attachment if we have data
        attachments = []
        if self.report_data:
            att = self.env['ir.attachment'].create({
                'name': self.pdf_filename or f'{self.report_type}_report.json',
                'datas': base64.b64encode(self.report_data.encode()),
                'mimetype': 'application/json',
            })
            attachments.append(att.id)

        for partner in schedule.recipient_ids:
            if not partner.email:
                continue
            mail = self.env['mail.mail'].create({
                'subject': subject,
                'body_html': body,
                'email_to': partner.email,
                'attachment_ids': [(6, 0, attachments)],
            })
            mail.send()

        self.state = 'sent'
        self.sent_date = fields.Datetime.now()
        _logger.info(
            'Report %s sent to %d recipients',
            schedule.name, len(schedule.recipient_ids),
        )

    def action_reset_to_generated(self):
        """Reset a failed or sent report back to generated state."""
        self.ensure_one()
        self.state = 'generated'
