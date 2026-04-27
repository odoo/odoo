from datetime import timedelta, datetime
from odoo.tools.xml_utils import cleanup_xml_node
from markupsafe import escape, Markup
from base64 import b64encode, b64decode
from pytz import timezone
from time import sleep
import psycopg2

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import SQL


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_ec_delivery_start_date = fields.Date(
        string="Start Date",
        compute='_compute_l10n_ec_delivery_guide_dates',
        copy=False,
        readonly=False,
        store=True,
        help="Ecuador: Date on which the transfer starts."
    )
    l10n_ec_delivery_end_date = fields.Date(
        string="End Date",
        compute='_compute_l10n_ec_delivery_guide_dates',
        copy=False,
        readonly=False,
        store=True,
        help="Ecuador: Date on which the transfer ends. By default, 15 days after the start date."
    )
    l10n_ec_transfer_reason = fields.Char(
        string="Transfer Reason",
        compute='_compute_l10n_ec_transfer_reason',
        copy=False,
        readonly=False,
        store=True,
        help="Ecuador: Reason for the transfer."
    )
    l10n_ec_transporter_id = fields.Many2one(
        comodel_name='res.partner',
        string="Transporter",
        help="Ecuador: Transporter of the goods."
    )
    l10n_ec_plate_number = fields.Char(
        string="Plate Number",
        copy=False,
        help="Ecuador: Plate number of the vehicle."
    )
    l10n_ec_edi_document_number = fields.Char(
        string="Delivery Guide Number (SRI)",
        copy=False,
        readonly=True,
    )
    l10n_ec_authorization_date = fields.Datetime(
        string="Authorization date",
        copy=False, readonly=True, tracking=True,
        help="Ecuador: Date on which government authorizes the document, unset if document is cancelled.",
    )
    l10n_ec_authorization_number = fields.Char(
        string="Authorization number",
        size=49,
        copy=False, index=True,
        tracking=True,
        readonly=True,
        help="Ecuador: EDI authorization number (same as access key), set upon posting",
    )
    # Delivery guide management
    l10n_ec_delivery_guide_error = fields.Html(
        string="Delivery guide error details",
        copy=False,
        help="Error details when sending the delivery guide.",
    )
    l10n_ec_edi_status = fields.Selection(
        selection=[
            ('to_send', "To Send"),
            ('sent', "Sent"),
            ('to_cancel', "To Cancel"),
            ('cancelled', "Cancelled"),
        ],
        string="Delivery Guide Status",
        copy=False,
        readonly=True,
        help="Status of the delivery guide.",
    )
    l10n_ec_allow_send_edi = fields.Boolean(
        string="Allow Send EDI",
        compute='_compute_l10n_ec_allow_send_edi',
        help="Ecuador: Allow to send the EDI document.",
    )
    l10n_ec_edi_content = fields.Binary(
        string="Delivery guide content (SRI)",
        help="Ecuador: Delivery guide content in XML format.",
    )
    l10n_ec_is_delivery_guide = fields.Boolean(
        string="Is Delivery Guide",
        compute='_compute_l10n_ec_is_delivery_guide',
        help="Ecuador: Allow to know when an stock picking is a Delivery Guide.",
    )

    @api.depends('scheduled_date')
    def _compute_l10n_ec_delivery_guide_dates(self):
        """
        Compute the delivery guide dates for the stock picking.

        This method calculates the start and end dates for the delivery guide
        based on the scheduled date of the stock picking. The start date is set
        to the same as the scheduled date, and the end date is set to 15 days
        after the scheduled date.

        :return: None
        """
        for stock_picking in self:
            stock_picking.l10n_ec_delivery_start_date = stock_picking.scheduled_date
            stock_picking.l10n_ec_delivery_end_date = stock_picking.scheduled_date + timedelta(days=15)

    @api.depends('location_dest_id')
    def _compute_l10n_ec_transfer_reason(self):
        """
        Compute the transfer reason for the stock picking based on the destination usage.

        The transfer reason is determined based on the usage of the destination location.
        If the destination usage is 'customer', the transfer reason is set as 'Goods Dispatch'.
        If the destination usage is 'supplier', the transfer reason is set as 'Goods Return'.
        If the destination usage is 'internal', the transfer reason is set as 'Internal Transfer'.
        For any other destination usage, the transfer reason is set as 'Others'.
        """
        destination_usage_map = {
            'customer': _("Goods Dispatch"),
            'supplier': _("Goods Return"),
            'internal': _("Internal Transfer"),
        }
        for stock_picking in self:
            destination_usage = stock_picking.location_dest_id.usage
            move_reason = destination_usage_map.get(destination_usage, _("Others"))
            stock_picking.l10n_ec_transfer_reason = move_reason

    @api.depends('state', 'l10n_ec_is_delivery_guide', 'l10n_ec_edi_status')
    def _compute_l10n_ec_allow_send_edi(self):
        """
        Compute the allow send EDI flag for the stock picking.
        """
        for stock_picking in self:
            stock_picking.l10n_ec_allow_send_edi = stock_picking.state == 'done' and \
                stock_picking.l10n_ec_is_delivery_guide and not stock_picking.l10n_ec_edi_status

    @api.depends('country_code', 'picking_type_code')
    def _compute_l10n_ec_is_delivery_guide(self):
        """
        Compute the is delivery guide flag for the stock picking.
        """
        for stock_picking in self:
            stock_picking.l10n_ec_is_delivery_guide = stock_picking.country_code == 'EC' and \
                stock_picking.location_id.usage == 'internal'

    def _l10n_ec_edi_validations(self):
        """
        Rum the validations for the delivery guide. At this time:
        - The source location must be internal
        - The transfer reason must be set
        - The transporter must be set
        - The plate number must be set
        - The warehouse must have an entity point set
        - The warehouse must have an emission point set
        """
        error_list = []
        if self.location_id.usage != 'internal':
            error_list.append(_("The source location must be internal"))
        if not self.l10n_ec_transfer_reason:
            error_list.append(_("The transfer reason is not set. Please set it before sending the delivery guide."))
        if not self.l10n_ec_transporter_id:
            error_list.append(_("The transporter is not set. Please set it before sending the delivery guide."))
        if not self.l10n_ec_plate_number:
            error_list.append(_("The plate number is not set. Please set it before sending the delivery guide."))
        if not self.picking_type_id.warehouse_id.l10n_ec_entity:
            error_list.append(_("The warehouse must have an entity point set. Please set it before sending the delivery guide."))
        if not self.picking_type_id.warehouse_id.l10n_ec_emission:
            error_list.append(_("The warehouse must have an emission point set. Please set it before sending the delivery guide."))
        if not self.l10n_ec_transporter_id.vat or not self.l10n_ec_transporter_id.l10n_latam_identification_type_id:
            error_list.append(_("The transporter must have a defined VAT and an identification type."))
        if not self.company_id.vat:
            error_list.append(_("You must set a VAT number for company %s", self.company_id.display_name))
        if not self.company_id.l10n_ec_legal_name:
            error_list.append(_("You must define a legal name in the settings for company %s", self.company_id.name))
        if not self.company_id.partner_id.street:
            error_list.append(_("You must define an address(street) in the settings for company %s", self.company_id.name))
        if not self.picking_type_id.warehouse_id.partner_id.street:
            error_list.append(_("You must define an address(street) for warehouse %s", self.picking_type_id.warehouse_id.name))
        if not self.partner_id.commercial_partner_id.vat:
            error_list.append(_("You must set a VAT number for partner %s", self.partner_id.commercial_partner_id.display_name))
        if not self.partner_id.street:
            error_list.append(_("You must define an address(street) for partner %s", self.partner_id.display_name))
        if error_list:
            raise UserError("\n".join(error_list))

    def l10n_ec_action_create_delivery_guide(self):
        """
        Create the delivery guide for the stock picking.
        Validate if warehouse has a sequence for delivery guides, if not, create one.
        Manage the delivery guide status and errors.
        """
        self._check_company()
        self._l10n_ec_edi_validations()
        account_edi_format_model = self.env['account.edi.format']
        for record in self:
            # == Generate a document number ==
            wh_id = record.picking_type_id.warehouse_id
            if not record.l10n_ec_edi_document_number:
                record.l10n_ec_edi_document_number = f'{wh_id.l10n_ec_entity}-{wh_id.l10n_ec_emission}-{wh_id.l10n_ec_delivery_number_sequence_id.next_by_id()}'
            record.l10n_ec_authorization_number = record._l10n_ec_get_authorization_number()

            # == Create and sign the delivery guide ==
            edi_str = record._l10n_ec_edi_create_delivery_guide()
            signed_edi_str = account_edi_format_model._l10n_ec_generate_signed_xml(record.company_id, edi_str)
            record.write({
                'l10n_ec_edi_status': 'to_send',
                'l10n_ec_edi_content': b64encode(signed_edi_str.encode()),
                'l10n_ec_delivery_guide_error': False,
            })

    def l10n_ec_send_delivery_guide_to_send(self):
        """
        Send the delivery guide for the stock picking records that are pending to be sent.
        This method filters the stock picking records to find those with an 'l10n_ec_edi_status' of 'to_send'.
        For each of these records, it decodes the EDI content, sends it for authorization, and updates the record
        based on the response.
        If there are errors during the authorization process and the context does not skip connection errors,
        the errors are recorded in 'l10n_ec_delivery_guide_error'. If the authorization is successful, the EDI
        content is updated and the status is set to 'sent'.

        """
        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute(SQL(
                    'SELECT 1 FROM %s WHERE id IN %s FOR UPDATE NOWAIT',
                    SQL.identifier(self._table),
                    tuple(self.ids),
                ))
        except psycopg2.errors.LockNotAvailable:
            if not self.env.context.get('cron_skip_connection_errs'):
                raise UserError(_('Some of these electronic documents are already being processed.')) from None
            return
        for record in self.filtered(lambda x: x.l10n_ec_edi_status == 'to_send'):
            signed_edi_str = b64decode(record.l10n_ec_edi_content).decode()
            errors, call_status, attachment = self._l10n_ec_send_xml_to_authorize(
                record,
                signed_edi_str
            )
            if call_status == 'error' and errors:
                if not self.env.context.get('cron_skip_connection_errs', False):
                    record.l10n_ec_delivery_guide_error = Markup("<br/>").join(escape(e) for e in errors)
            else:
                record.write({
                    'l10n_ec_delivery_guide_error': False,
                    'l10n_ec_edi_status': 'sent',
                    'l10n_ec_edi_content': attachment.datas,
                })

    def l10n_ec_send_delivery_guide_to_partner(self):
        '''
        Send the delivery guide to the partner.
        '''
        self.ensure_one()
        if not self.partner_id.email:
            raise UserError(_("The partner does not have an email address."))
        template = self.env.ref('l10n_ec_edi_stock.email_template_edi_delivery_guide')
        xml_attachment = self.env['ir.attachment'].create({
            'name': f'GuíRe {self.l10n_ec_edi_document_number}.xml',
            'type': 'binary',
            'datas': self.l10n_ec_edi_content,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/xml',
        })
        pdf_action = self.env.ref('l10n_ec_edi_stock.action_delivery_guide_report_pdf')
        pdf_content, __ = self.env['ir.actions.report'].sudo()._render_qweb_pdf(pdf_action, self.id)
        pdf_attachment = self.env['ir.attachment'].create({
            'name': f'GuíRe {self.l10n_ec_edi_document_number}.pdf',
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
            'attachment_ids': [(4, pdf_attachment.id), (4, xml_attachment.id)],
        })
        composer._action_send_mail()

    def l10n_ec_action_download_delivery_guide(self):
        """
        Download the delivery guide xml for the stock picking.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/stock.picking/%s/l10n_ec_edi_content?download=true&filename=%s' % (
                self.id, f'GuíRe {self.l10n_ec_edi_document_number}.xml',
            ),
            'target': 'self',
        }

    def _l10n_ec_edi_create_delivery_guide(self):
        """
        Create the XML request content for the delivery guide.
        """
        self.ensure_one()
        values = self._l10n_ec_edi_get_delivery_guide_values()
        xml_string = self.env['ir.qweb']._render(
            'l10n_ec_edi_stock.sri_delivery_guide',
            values
        )
        xml_content = cleanup_xml_node(xml_string)
        return xml_content

    def _l10n_ec_edi_get_delivery_guide_values(self):
        '''
        Get the values to render the delivery guide XML template.
        '''
        self.ensure_one()
        return {
            'record': self,
            'l10n_ec_production_env': '2' if self.company_id.l10n_ec_production_env else '1',
            'l10n_ec_legal_name': self.company_id.l10n_ec_legal_name,
            'commercial_company_name': self.company_id.partner_id.commercial_company_name,
            'company_vat': self.company_id.partner_id.vat,
            'l10n_ec_authorization_number': self.l10n_ec_authorization_number,
            'l10n_ec_entity': self.picking_type_id.warehouse_id.l10n_ec_entity,
            'l10n_ec_emission': self.picking_type_id.warehouse_id.l10n_ec_emission,
            'sequence': self.l10n_ec_edi_document_number.split('-')[-1],
            'company_street': self.company_id.street,
            'warehouse_street': self.picking_type_id.warehouse_id.partner_id.street,
            'l10n_ec_transporter_name': self.l10n_ec_transporter_id.name,
            'l10n_ec_transporter_sri_code': self.l10n_ec_transporter_id._get_sri_code_for_partner().value,
            'l10n_ec_transporter_vat': self.l10n_ec_transporter_id.vat,
            'l10n_ec_forced_accounting': 'SI' if self.company_id.l10n_ec_forced_accounting else 'NO',
            'l10n_ec_special_taxpayer_number': self.company_id.l10n_ec_special_taxpayer_number,
            'l10n_ec_delivery_start_date': self.l10n_ec_delivery_start_date.strftime('%d/%m/%Y'),
            'l10n_ec_delivery_end_date': self.l10n_ec_delivery_end_date.strftime('%d/%m/%Y'),
            'l10n_ec_plate_number': self.l10n_ec_plate_number.replace('-', ''),
            'partner_vat': self.partner_id.commercial_partner_id.vat,
            'partner_name': self.partner_id.commercial_partner_id.name,
            'partner_address': self.partner_id._display_address().replace('\n', ' - '),
            'l10n_ec_transfer_reason': self.l10n_ec_transfer_reason,
            'lines': [{
                'product_barcode': line.product_id.barcode or line.product_id.default_code or 'N/A', # TODO: remove in master and keep main_code
                'main_code': line.product_id.barcode or line.product_id.default_code or 'N/A',
                'l10n_ec_auxiliary_code': line.product_id.l10n_ec_auxiliary_code or '',
                'product_partner_ref': line.product_id.with_context(lang=self.partner_id.lang).partner_ref,
                'qty_done': line.quantity,
                'lot_id': line.lot_id,
            } for line in self.mapped('move_line_ids_without_package')],
            'note': self.note.striptags().replace('\n', ' ')[:300] if self.note else None,
            'origin': self.origin or None,
        }

    def _l10n_ec_get_authorization_number(self):
        """
        Generate the authorization number for the delivery guide.
        """
        self.ensure_one()
        company = self.company_id
        wh_id = self.picking_type_id.warehouse_id
        document_code_sri = '06'  # 06 is the code for electronic guide
        environment = company.l10n_ec_production_env and '2' or '1'
        serie = wh_id.l10n_ec_entity + wh_id.l10n_ec_emission
        sequential = self.l10n_ec_edi_document_number.split('-')[-1]
        num_filler = '31215214'  # can be any 8 digits, thanks @3cloud !
        emission = '1'  # corresponds to "normal" emission, "contingencia" no longer supported
        now_date = self.l10n_ec_delivery_start_date.strftime('%d%m%Y')
        key_value = now_date + document_code_sri + company.partner_id.vat + \
            environment + serie + sequential + num_filler + emission
        return key_value + str(self._l10n_ec_get_check_digit(key_value))

    @api.model
    def _l10n_ec_get_check_digit(self, key):
        '''
        Get the check digit for the authorization number
        '''
        sum_total = sum(int(key[-i - 1]) * (i % 6 + 2) for i in range(len(key)))
        sum_check = 11 - (sum_total % 11)
        if sum_check >= 10:
            sum_check = 11 - sum_check
        return sum_check

    def button_action_cancel_delivery_guide(self):
        """
        Request the cancellation of the delivery guide.
        """
        self.ensure_one()
        self.message_post(body=_("A cancellation of the Delivery Guide has been requested."))
        self.l10n_ec_edi_status = 'to_cancel'

    def l10n_ec_send_delivery_guide_to_cancel(self):
        '''
        Send the delivery guide for the stock picking records that are pending to be cancelled.
        '''
        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute(SQL(
                    'SELECT 1 FROM %s WHERE id IN %s FOR UPDATE NOWAIT',
                    SQL.identifier(self._table),
                    tuple(self.ids),
                ))
        except psycopg2.errors.LockNotAvailable:
            if not self.env.context.get('cron_skip_connection_errs'):
                raise UserError(_('Some of these electronic documents are already being processed.')) from None
            return
        for record in self.filtered(lambda x: x.l10n_ec_edi_status == 'to_cancel'):
            result = self.env['account.edi.format']._l10n_ec_cancel_move_edi(record)
            errors = result[record].get('error')
            success = result[record].get('success')
            if not success and errors:
                if not self.env.context.get('cron_skip_connection_errs', False):
                    record.l10n_ec_delivery_guide_error = errors
            else:
                record.write({
                    'l10n_ec_delivery_guide_error': False,
                    'l10n_ec_edi_status': 'cancelled',
                })

    def _l10n_ec_send_xml_to_authorize(self, picking, xml_string):
        '''
        Send the XML to the government to authorize it.
        If the document has already been authorized, it will not be sent again.
        '''
        # === DEMO ENVIRONMENT REPONSE ===
        if picking.company_id._l10n_ec_is_demo_environment():
            return self._l10n_ec_generate_demo_xml_attachment(picking, xml_string)

        # === Try sending and getting authorization status === #
        errors, error_type, auth_date, auth_num = self.env['account.edi.format']._l10n_ec_send_document(
            picking.company_id,
            picking.l10n_ec_authorization_number,
            xml_string,
            already_sent=picking.l10n_ec_authorization_date,
        )
        attachment = False
        if auth_num and auth_date:
            picking.l10n_ec_authorization_date = auth_date.replace(tzinfo=None)
            attachment = self.env['ir.attachment'].create({
                'name': f'GuíRe {picking.l10n_ec_edi_document_number}.xml',
                'res_id': picking.id,
                'res_model': picking._name,
                'type': 'binary',
                'raw': self.env['account.edi.format']._l10n_ec_create_authorization_file_new(picking.company_id, xml_string, auth_num, auth_date),
                'mimetype': 'application/xml',
                'description': f"Ecuadorian electronic document generated for document {picking.display_name}."
            })
            picking.with_context(no_new_invoice=True).message_post(
                body=escape(
                    _(
                        "Electronic document authorized.{}Authorization num:{}%(authorization_num)s{}Authorization date:{}%(authorization_date)s",
                        authorization_num=picking.l10n_ec_authorization_number, authorization_date=picking.l10n_ec_authorization_date,
                    )
                ).format(Markup('<br/><strong>'), Markup('</strong><br/>'), Markup('<br/><strong>'), Markup('</strong><br/>')),
                attachment_ids=attachment.ids,
            )

        return errors, error_type, attachment

    def _l10n_ec_generate_demo_xml_attachment(self, picking, xml_string):
        """
        Generates an xml attachment to simulate a response from the SRI without the need for a digital signature.
        """
        picking.l10n_ec_authorization_date = datetime.now(tz=timezone('America/Guayaquil')).date()
        attachment = self.env['ir.attachment'].create({
            'name': f'GuíRe {picking.l10n_ec_edi_document_number}.xml',
            'res_id': picking.id,
            'res_model': picking._name,
            'type': 'binary',
            'raw': self.env['account.edi.format']._l10n_ec_create_authorization_file_new(
                picking.company_id, xml_string,
                picking.l10n_ec_authorization_number, picking.l10n_ec_authorization_date),
            'mimetype': 'application/xml',
            'description': f"Ecuadorian electronic document generated for document {picking.display_name}."
        })
        picking.with_context(no_new_invoice=True).message_post(
            body=escape(
                _(
                    "{}This is a DEMO response, which means this document was not sent to the SRI.{}If you want your document to be processed by the SRI, please set an {}Electronic Certificate File{} in the settings.{}Demo electronic document.{}Authorization num:{}%(authorization_num)s{}Authorization date:{}%(authorization_date)s",
                    authorization_num=picking.l10n_ec_authorization_number, authorization_date=picking.l10n_ec_authorization_date
                )
            ).format(Markup('<strong>'), Markup('</strong><br/>'), Markup('<strong>'), Markup('</strong>'), Markup('<br/><br/>'), Markup('<br/><strong>'), Markup('</strong><br/>'), Markup('<br/><strong>'), Markup('</strong><br/>')),
            attachment_ids=attachment.ids,
        )
        return [], "", attachment

    def _l10n_ec_cron_send_delivery_guide_to_sri(self):
        """
        Send the delivery guide for the stock picking records that are pending to be sent.
        """
        for record in self.search([('l10n_ec_edi_status', 'in', ('to_send', 'to_cancel'))]):
            if record.l10n_ec_edi_status == 'to_cancel':
                record.with_context(cron_skip_connection_errs=True).l10n_ec_send_delivery_guide_to_cancel()
            else:
                record.with_context(cron_skip_connection_errs=True).l10n_ec_send_delivery_guide_to_send()
            self.env.cr.commit()
            sleep(1)

    def _l10n_ec_get_delivery_guide_additional_info(self):
        """
        Get the additional information for the delivery guide.
        """
        return {
            'Referencia': f'GuíRe {self.l10n_ec_edi_document_number or "/"}',
            'E-mail': self.partner_id.email or '',
            'Dirección': self.partner_id.street or '',
            'Teléfono': self.partner_id.phone or '',
        }
