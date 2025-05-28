from base64 import b64encode

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_ar_delivery_guide_number = fields.Char(
        string="Delivery Guide No.",
        copy=False,
        readonly=True,
    )
    l10n_ar_cai_data = fields.Json(string="CAI Data", copy=False)
    l10n_ar_allow_generate_delivery_guide = fields.Boolean(
        compute="_compute_l10n_ar_delivery_guide_flags",
    )
    l10n_ar_allow_send_delivery_guide = fields.Boolean(
        compute="_compute_l10n_ar_delivery_guide_flags",
    )

    # === COMPUTE METHODS === #

    @api.depends('state', 'l10n_ar_delivery_guide_number', 'picking_type_id.l10n_ar_document_type_id')
    def _compute_l10n_ar_delivery_guide_flags(self):
        """
        Compute flags for allowing delivery guide generation and sending.
        - Generation allowed if: state is 'done', document type exists, and no guide number.
        - Send allowed if: guide number exists.
        """
        for picking in self:
            has_doc_type = bool(picking.picking_type_id.l10n_ar_document_type_id)
            picking.l10n_ar_allow_generate_delivery_guide = (
                picking.state == 'done' and has_doc_type and not picking.l10n_ar_delivery_guide_number
            )
            picking.l10n_ar_allow_send_delivery_guide = bool(picking.l10n_ar_delivery_guide_number)

    # === BUSINESS METHODS === #

    def l10n_ar_action_create_delivery_guide(self):
        """
        Create the delivery guide number and store CAI data for the stock picking.
        """
        self.ensure_one()

        if not self.l10n_ar_delivery_guide_number:
            picking_type = self.picking_type_id
            new_sequence_number = picking_type.l10n_ar_next_delivery_number
            delivery_guide_number = picking_type.l10n_ar_sequence_id.next_by_id()
            if not int(picking_type.l10n_ar_sequence_number_start) <= new_sequence_number <= int(picking_type.l10n_ar_sequence_number_end):
                raise UserError(_("The delivery guide number %s exceeds the range specified in the CAI. Please update the range or use a different CAI with a different range.", delivery_guide_number))
            self.l10n_ar_delivery_guide_number = delivery_guide_number
            self.l10n_ar_cai_data = {
                'document_type_id': picking_type.l10n_ar_document_type_id.id,
                'cai_authorization_code': picking_type.l10n_ar_cai_authorization_code,
                'cai_expiration_date': picking_type.l10n_ar_cai_expiration_date.strftime('%Y-%m-%d'),
                'sequence_number_start': picking_type.l10n_ar_sequence_number_start,
                'sequence_number_end': picking_type.l10n_ar_sequence_number_end,
            }

    def l10n_ar_action_send_delivery_guide(self):
        """
        Send the delivery guide to the partner.
        """
        self.ensure_one()
        if not self.partner_id.email:
            raise UserError(_("The partner does not have an email address."))
        template = self.env.ref('l10n_ar_stock.email_template_ar_remitos_delivery_guide')
        pdf_action = self.env.ref('l10n_ar_stock.action_delivery_guide_report_pdf')
        pdf_content, __ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(pdf_action, self.id)
        pdf_attachment = self.env['ir.attachment'].create({
            'name': f'Remito - {self.l10n_ar_delivery_guide_number}.pdf',
            'type': 'binary',
            'datas': b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        composer = self.env['mail.compose.message'].with_context(
            default_model='stock.picking',
            active_model='stock.picking',
            active_id=self.id,
            default_res_ids=self.ids,
            default_use_template=True,
            default_template_id=template.id,
            default_composition_mode='comment',
            default_email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature',
            force_email=True,
        ).create({
            'attachment_ids': pdf_attachment.ids,
        })
        composer._action_send_mail()
