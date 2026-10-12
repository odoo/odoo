# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_th_wth_condition = fields.Selection(
        string="Withholding Condition",
        selection=[
            ('at_source', 'Withhold at source'),
            ('forever', 'Paid by payer (Forever/Gross-up)'),
            ('one_time', 'Paid by payer (One-time)'),
        ],
        compute='_compute_l10n_th_wth_condition',
        store=True,
        readonly=False,
        tracking=True,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('withhold', 'country_code')
    def _compute_l10n_th_wth_condition(self):
        """
        Compute the default value only if relevant for the current payment's country.
        """
        for payment in self:
            if payment.withhold != 'payment' and payment.country_code == 'TH':
                payment.l10n_th_wth_condition = payment.l10n_th_wth_condition or 'at_source'
            else:
                payment.l10n_th_wth_condition = False

    # --------------
    # Action methods
    # --------------

    def action_l10n_th_print_50_tawi(self):
        """
        Triggered by the 'Print 50 Tawi' button.
        """
        return self.env.ref('l10n_th.action_report_50_tawi').report_action(self, config=False)

    def action_download_50_tawi_bulk(self):
        """
        Triggered by the 'Thailand: 50 tawi' bulk print action.
        Validates the records and downloads a ZIP containing individual PDF reports,
        """
        invalid_payments = self.filtered(
            lambda p: p.state not in ['paid', 'reconciled'] or p.payment_type == 'inbound' or p.country_code != 'TH' or not p.withholding_line_ids,
        )
        valid_payments = self - invalid_payments

        if not valid_payments:
            raise UserError(_("No eligible payments found for 50 Tawi report."))

        report_action = self.env.ref('l10n_th.action_report_50_tawi')
        attachments = self.env['ir.attachment']
        for payment in valid_payments:
            pdf_content, _report_type = report_action.sudo()._render_qweb_pdf("l10n_th.report_50_tawi", res_ids=[payment.id])
            report_filename = 'WHT_%s.pdf' % (payment.name.replace('/', '-'))

            attachment = self.env['ir.attachment'].create({
                'name': report_filename,
                'type': 'binary',
                'raw': pdf_content,
                'res_model': 'account.payment',
                'res_id': payment.id,
                'mimetype': 'application/pdf',
            })
            attachments += attachment

        download_action = {
            'type': 'ir.actions.act_url',
            'url': f'/l10n_th/download_tawi_reports/{",".join(map(str, attachments.ids))}',
        }

        if invalid_payments:
            invalid_list = ", ".join(invalid_payments.mapped('display_name'))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Notification"),
                    'message': _("Invalid payments skipped: %s. The process will continue and print the valid payments.", invalid_list),
                    'type': 'warning',
                    'sticky': True,
                    'next': download_action,
                },
            }

        return download_action
