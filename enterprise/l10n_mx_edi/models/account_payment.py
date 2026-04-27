# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_mx_edi_payment_method_id = fields.Many2one(related='move_id.l10n_mx_edi_payment_method_id', readonly=False)
    l10n_mx_edi_cfdi_origin = fields.Char(related='move_id.l10n_mx_edi_cfdi_origin', readonly=False)
    l10n_mx_edi_cfdi_uuid = fields.Char(related='move_id.l10n_mx_edi_cfdi_uuid', readonly=False)
    l10n_mx_edi_cfdi_state = fields.Selection(related='move_id.l10n_mx_edi_cfdi_state', readonly=False)
    l10n_mx_edi_cfdi_cancel_id = fields.Many2one(related='move_id.l10n_mx_edi_cfdi_cancel_id', readonly=False)
    l10n_mx_edi_cfdi_sat_state = fields.Selection(related='move_id.l10n_mx_edi_cfdi_sat_state', readonly=False)
    l10n_mx_edi_payment_document_ids = fields.One2many(related='move_id.l10n_mx_edi_payment_document_ids', readonly=False)
    l10n_mx_edi_force_pue_payment_needed = fields.Boolean(related='move_id.l10n_mx_edi_force_pue_payment_needed', readonly=False)
    l10n_mx_edi_is_cfdi_needed = fields.Boolean(related='move_id.l10n_mx_edi_is_cfdi_needed', readonly=False)
    l10n_mx_edi_update_sat_needed = fields.Boolean(related='move_id.l10n_mx_edi_update_sat_needed', readonly=False)
    l10n_mx_edi_cfdi_attachment_id = fields.Many2one(related='move_id.l10n_mx_edi_cfdi_attachment_id', readonly=False)

    def _get_payment_receipt_report_values(self):
        # EXTENDS 'account'
        values = super()._get_payment_receipt_report_values()

        cfdi_infos = self.move_id and self.move_id._l10n_mx_edi_get_extra_payment_report_values()
        if cfdi_infos:
            values.update({
                'display_invoices': False,
                'display_payment_method': False,
                'cfdi': cfdi_infos,
            })

        return values

    def l10n_mx_edi_cfdi_payment_force_try_send(self):
        self.move_id.l10n_mx_edi_cfdi_payment_force_try_send()

    def l10n_mx_edi_cfdi_try_sat(self):
        self.move_id.l10n_mx_edi_cfdi_try_sat()

    def _process_attachments_for_template_post(self, mail_template):
        """ Add CFDI attachment to template. """
        result = super()._process_attachments_for_template_post(mail_template)
        for payment in self.filtered('l10n_mx_edi_cfdi_attachment_id'):
            payment_result = result.setdefault(payment.id, {})
            payment_result.setdefault('attachment_ids', []).append(payment.l10n_mx_edi_cfdi_attachment_id.id)
        return result
