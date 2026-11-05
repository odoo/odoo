import logging

import requests
from lxml import etree

from odoo import api, fields, models
from odoo.exceptions import LockError, UserError

from odoo.addons.l10n_ar.tools.partner_identifiers import (
    AR_CUIT_AFIP_CODE,
    AR_STATE_TO_CI_AFIP_CODE,
)

_logger = logging.getLogger(__name__)

COT_DOCUMENT_TYPES = {
    '89': 'LE',
    '90': 'LC',
    '94': 'PAS',
    '96': 'DNI',
    **dict.fromkeys(AR_STATE_TO_CI_AFIP_CODE.values(), 'CI'),
}


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_ar_delivery_guide_number = fields.Char(
        string="Delivery Guide No.",
        copy=False,
    )
    l10n_ar_cai_data = fields.Json(string="CAI Data", copy=False)
    l10n_ar_allow_generate_delivery_guide = fields.Boolean(
        compute="_compute_l10n_ar_delivery_guide_flags",
    )
    l10n_ar_allow_send_delivery_guide = fields.Boolean(
        compute="_compute_l10n_ar_delivery_guide_flags",
    )
    l10n_ar_delivery_guide_cron_user_id = fields.Many2one(
        comodel_name="res.users",
        readonly=True,
        copy=False,
    )
    l10n_ar_is_cot_enabled = fields.Boolean(
        compute='_compute_l10n_ar_is_cot_enabled',
    )
    l10n_ar_cot_departure_date = fields.Datetime(
        string="Transport Departure Date",
        copy=False,
    )
    l10n_ar_cot_license_plate = fields.Char(
        string="Vehicle License Plate",
        copy=False,
        help="Argentina: Enter 3 letters followed by 3 numbers, or 2 letters followed by 3 numbers and 2 letters.",
    )
    l10n_ar_cot_is_non_finished_product = fields.Boolean(
        string="Is Non Finished Product",
        copy=False,
    )
    l10n_ar_cot_amount = fields.Float(
        string="Net Amount of the Goods",
        default=0.0,
        copy=False,
        help="Argentina: Enter the declared net amount of the goods.",
    )
    l10n_ar_cot_number = fields.Char(
        string="COT Number",
        readonly=True,
        copy=False,
    )
    l10n_ar_cot_error = fields.Text(
        string="COT Error",
        readonly=True,
        copy=False,
    )
    l10n_ar_cot_carrier_id = fields.Many2one(
        comodel_name='res.partner',
        string="Transport Carrier",
        copy=False,
        check_company=True,
        help="Argentina: Contact transporting the goods, its CUIT is reported in the COT.",
    )

    # === COMPUTE METHODS === #

    @api.depends('state', 'l10n_ar_delivery_guide_number', 'picking_type_id.l10n_ar_document_type_id', 'picking_type_id.code')
    def _compute_l10n_ar_delivery_guide_flags(self):
        """
        Compute flags for allowing delivery guide generation and sending.
        - Generation allowed if: state is 'done', document type exists, and no guide number.
        - Send allowed if: guide number exists on outgoing pickings.
        """
        for picking in self:
            has_doc_type = bool(picking.picking_type_id.l10n_ar_document_type_id)
            picking.l10n_ar_allow_generate_delivery_guide = (
                picking.state == 'done' and has_doc_type and not picking.l10n_ar_delivery_guide_number
            )
            picking.l10n_ar_allow_send_delivery_guide = picking.l10n_ar_delivery_guide_number and picking.picking_type_id.code == 'outgoing'

    @api.depends('company_id')
    def _compute_l10n_ar_is_cot_enabled(self):
        for picking in self:
            picking.l10n_ar_is_cot_enabled = bool(picking.company_id.sudo()._l10n_ar_get_arba_cot_company().l10n_ar_arba_cot_environment)

    # === BUSINESS METHODS === #

    def l10n_ar_action_create_delivery_guide(self):
        """
        Create the delivery guide number and store CAI data for the selected stock pickings.
        """
        already_generated, not_done, no_doc_type, _valid = self.partitioned(
            'l10n_ar_delivery_guide_number',
            lambda picking: picking.state != 'done',
            lambda picking: not picking.picking_type_id.l10n_ar_document_type_id,
        )
        errors = []
        if already_generated:
            errors.append(self.env._("- %(names)s already have a delivery guide.", names=already_generated.mapped('name')))
        if not_done:
            errors.append(self.env._("- %(names)s must be validated before generating a delivery guide.", names=not_done.mapped('name')))
        if no_doc_type:
            errors.append(self.env._("- The operation types on the deliveries are not configured for delivery guides: %(names)s.", names=no_doc_type.mapped('name')))
        if errors:
            raise UserError(self.env._("Cannot generate delivery guides for the following transfers:\n%(transfers)s", transfers="\n".join(errors)))

        for picking in self:
            picking_type = picking.picking_type_id
            sequence_start = picking_type.l10n_ar_sequence_number_start
            sequence_end = picking_type.l10n_ar_sequence_number_end
            new_sequence_number = picking_type.l10n_ar_next_delivery_number
            delivery_guide_number = picking_type.l10n_ar_sequence_id.next_by_id()
            if (
                sequence_start
                and sequence_end
                and picking_type.l10n_ar_cai_authorization_code
                and not (int(sequence_start) <= new_sequence_number <= int(sequence_end))
            ):
                raise UserError(self.env._("The delivery guide number %s exceeds the range specified in the CAI. Please update the range or use a different CAI with a different range.", delivery_guide_number))
            picking.l10n_ar_delivery_guide_number = delivery_guide_number
            picking.l10n_ar_cai_data = {
                'document_type_id': picking_type.l10n_ar_document_type_id.id,
                'cai_authorization_code': picking_type.l10n_ar_cai_authorization_code,
                'cai_expiration_date': picking_type.l10n_ar_cai_expiration_date and picking_type.l10n_ar_cai_expiration_date.strftime('%Y-%m-%d'),
                'sequence_number_start': sequence_start,
                'sequence_number_end': sequence_end,
            }

    def l10n_ar_action_send_delivery_guide(self, do_async=False):
        """ Send the delivery guide to the proper partners.
            :param do_async: If True, queue the sending via cron instead of sending immediately."""
        self._l10n_ar_validate_send_delivery_guide()
        if not do_async:
            self._l10n_ar_send_delivery_guide(force_send=True)
            return None
        self.l10n_ar_delivery_guide_cron_user_id = self.env.user
        self.env.ref('l10n_ar_stock.ir_cron_l10n_ar_send_delivery_guide')._trigger()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'title': self.env._('Processing Delivery Guides'),
                'message': self.env._('Delivery guides are being sent in the background.'),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def _l10n_ar_validate_send_delivery_guide(self, do_async=False):
        """ Validate that all pickings in self are eligible for sending delivery guides. """
        no_doc_type, no_number, no_email, already_queued, _valid = self.partitioned(
            lambda picking: not picking.picking_type_id.l10n_ar_document_type_id,
            lambda picking: not picking.l10n_ar_delivery_guide_number,
            lambda picking: not picking.partner_id.email,
            'l10n_ar_delivery_guide_cron_user_id',
        )
        if do_async:
            # We don't care about already_queued as this is call during the queued cron.
            return {
                'no_doc_type': no_doc_type,
                'no_number': no_number,
                'no_email': no_email,
                'all_errors': no_doc_type + no_number + no_email,
            }
        errors = []
        if no_doc_type:
            errors.append(self.env._("- The operation types on the deliveries are not configured for delivery guides: %(names)s.", names=no_doc_type.mapped('name')))
        if no_number:
            errors.append(self.env._("- No delivery guide has been generated yet for the following deliveries: %(names)s.", names=no_number.mapped('name')))
        if no_email:
            errors.append(self.env._("- The contacts on the following deliveries have no email address: %(names)s.", names=no_email.mapped('name')))
        if already_queued:
            errors.append(self.env._("- The following deliveries are already queued for sending: %(names)s.", names=already_queued.mapped('name')))
        if errors:
            raise UserError(self.env._("Cannot send delivery guides for the following transfers:\n%(transfers)s", transfers="\n".join(errors)))
        return {}

    def _l10n_ar_send_delivery_guide(self, force_send=False):
        """ Send the delivery guide email for each picking in self.

        PDFs are rendered in a single wkhtmltopdf call and split per record,
        which is dramatically faster than per-record rendering for batches.
        """
        template = self.env.ref('l10n_ar_stock.email_template_ar_remitos_delivery_guide')
        pdf_action = self.env.ref('l10n_ar_stock.action_delivery_guide_report_pdf')

        pdf_contents = self._l10n_ar_render_delivery_guide_pdfs(pdf_action)

        attachment_vals = [{
            'name': f'Remito - {picking.l10n_ar_delivery_guide_number}.pdf',
            'type': 'binary',
            'raw': pdf_contents[picking.id],
            'res_model': self._name,
            'res_id': picking.id,
            'mimetype': 'application/pdf',
        } for picking in self]
        attachments = self.env['ir.attachment'].create(attachment_vals)

        for picking, attachment in zip(self, attachments):
            picking.with_context(
                mail_notify_force_send=force_send,
            ).message_post_with_source(
                template,
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature',
                attachment_ids=attachment.ids,
            )

    def _l10n_ar_render_delivery_guide_pdfs(self, pdf_action):
        """ Batch-render delivery guide PDFs, returning {picking_id: pdf_bytes}.

        Falls back to per-record rendering if the batched merge step fails
        (wkhtmltopdf can refuse to merge multiple documents on unpatched QT,
        and the merge helper raises UserError when pypdf can't stitch the
        intermediate PDFs together).
        """
        report_sudo = self.env['ir.actions.report'].sudo()
        try:
            collected_streams, report_type = report_sudo._pre_render_qweb_pdf(pdf_action, self.ids)
            if report_type != 'pdf':
                # In test environments _pre_render_qweb_pdf falls back to
                # _render_qweb_html which returns raw bytes, not a stream dict.
                return {picking.id: collected_streams for picking in self}
            return {
                res_id: stream_data['stream'].getvalue()
                for res_id, stream_data in collected_streams.items()
                if stream_data.get('stream')
            }
        except UserError:
            pdf_contents = {}
            for picking in self:
                pdf_content, _unused = report_sudo._render_qweb_pdf(pdf_action, picking.id)
                pdf_contents[picking.id] = pdf_content
            return pdf_contents

    # === CRON METHODS === #

    def _l10n_ar_handle_cron_failures(self, errors):
        """ Dequeue failed records: log in chatter, notify users, clear cron field. """
        failed = errors['all_errors']
        error_messages = {
            'no_doc_type': self.env._("Delivery guide could not be sent: the operation type is not configured for delivery guides."),
            'no_number': self.env._("Delivery guide could not be sent: no delivery guide number has been generated."),
            'no_email': self.env._("Delivery guide could not be sent: the contact has no email address."),
        }
        for error_key, message in error_messages.items():
            for picking in errors.get(error_key, self.env['stock.picking']):
                picking.message_post(body=message, message_type='notification')
        for user, user_pickings in failed.grouped('l10n_ar_delivery_guide_cron_user_id').items():
            user._bus_send(
                'account_notification',
                {
                    'type': 'warning',
                    'title': self.env._('Delivery Guide Send Failed'),
                    'message': self.env._(
                        'The following Delivery Guides could not be sent due to validation errors:\n%(errors)s',
                        errors="\n".join(user_pickings.mapped('name')),
                    ),
                    'action_button': {
                        'name': self.env._('Open'),
                        'action_name': self.env._('Failed Delivery Guides'),
                        'model': 'stock.picking',
                        'res_ids': user_pickings.ids,
                    },
                },
            )
        failed.write({'l10n_ar_delivery_guide_cron_user_id': False})

    def _cron_l10n_ar_send_delivery_guide(self, batch_size=50):
        """ Cron method: process queued delivery guide sends in batches. """
        domain = [
            ('l10n_ar_delivery_guide_cron_user_id', '!=', False),
        ]
        records = self.search(domain, order='id asc', limit=batch_size).try_lock_for_update()
        records_len = len(records)
        if not records:
            return

        # Re-validate: fields may have changed since queueing.
        errors = records._l10n_ar_validate_send_delivery_guide(do_async=True)
        if errors.get('all_errors'):
            self._l10n_ar_handle_cron_failures(errors)
            records -= errors['all_errors']

        if not records:
            remaining = self.search_count(domain)
            self.env['ir.cron']._commit_progress(records_len, remaining=remaining)
            return

        pickings_by_user = records.grouped('l10n_ar_delivery_guide_cron_user_id')
        for user, user_pickings in pickings_by_user.items():
            user_pickings.with_user(user)._l10n_ar_send_delivery_guide()

        for user, user_pickings in pickings_by_user.items():
            user._bus_send(
                'account_notification',
                {
                    'type': 'success',
                    'title': self.env._('Delivery Guides Sent'),
                    'message': self.env._('The following Delivery Guide emails have been sent successfully.'),
                    'action_button': {
                        'name': self.env._('Open'),
                        'action_name': self.env._('Sent Delivery Guides'),
                        'model': 'stock.picking',
                        'res_ids': user_pickings.ids,
                    },
                },
            )
        records.write({'l10n_ar_delivery_guide_cron_user_id': False})

        remaining = self.search_count(domain)
        self.env['ir.cron']._commit_progress(records_len, remaining=remaining)

    # === ARBA/COT METHODS === #

    def _l10n_ar_check_cot_data(self):
        self.ensure_one()
        origin = self.picking_type_id.warehouse_id.partner_id
        products = self.move_ids.filtered('quantity').product_id
        if self.country_code != 'AR' or self.picking_type_code != 'outgoing' or not self.l10n_ar_delivery_guide_number or self.l10n_ar_cot_number:
            raise UserError(self.env._("A COT can only be generated once, for an outgoing transfer with a delivery guide."))
        if not self.l10n_ar_is_cot_enabled:
            raise UserError(self.env._("Select an ARBA COT Environment in the settings to generate a COT."))
        errors = []
        if not self.company_id.sudo()._l10n_ar_get_arba_cot_company().vat:
            errors.append(self.env._("The company has no CUIT."))
        if not self.l10n_ar_cot_license_plate:
            errors.append(self.env._("The Vehicle License Plate is missing."))
        if not self.l10n_ar_cot_carrier_id.vat:
            errors.append(self.env._("The carrier or its CUIT is missing."))
        if not self.l10n_ar_cot_is_non_finished_product and self.l10n_ar_cot_amount <= 0:
            errors.append(self.env._("The Net Amount of the Goods must be greater than 0."))
        for partner in (self.partner_id, origin):
            if not (partner.street and partner.zip and partner.city and partner.state_id):
                errors.append(self.env._(
                    "The street, zip, city and state of the address %s are required.",
                    partner.display_name or self.picking_type_id.warehouse_id.display_name,
                ))
        if no_reference := products.filtered(lambda product: not product.default_code):
            errors.append(self.env._("Products without Reference: %s", ", ".join(no_reference.mapped('display_name'))))
        if no_arba_code := products.filtered(lambda product: not product.l10n_ar_arba_code):
            errors.append(self.env._("Products without ARBA Code: %s", ", ".join(no_arba_code.mapped('display_name'))))
        if no_unit_code := products.uom_id.filtered(lambda uom: not uom.l10n_ar_arba_unit_code):
            errors.append(self.env._("Units of measure without ARBA Unit of Measure Code: %s", ", ".join(no_unit_code.mapped('name'))))
        if errors:
            raise UserError(self.env._("The COT cannot be generated:\n%s", "\n".join(f"- {error}" for error in errors)))

    def _l10n_ar_get_cot_unique_code(self):
        self.ensure_one()
        document_type = self.env['l10n_latam.document.type'].browse(self.l10n_ar_cai_data['document_type_id'])
        return document_type.code.zfill(3) + self.l10n_ar_delivery_guide_number.replace('-', '')

    def _l10n_ar_get_cot_txt(self, emission_date):
        """ Specification: https://www.arba.gov.ar/archivos/Publicaciones/nuevodiseniodearchivotxt.pdf """
        self.ensure_one()

        def sanitize(value):
            # '|' and '\n' separate the COT fields and records
            return value.replace('|', '').replace('\n', '')

        def get_address(partner):
            # The street number stays in the street, 'S/N' as suffix lets ARBA accept an empty number
            return [partner.street[:40], '', 'S/N', '', '', '', partner.zip, partner.city[:50], partner.state_id.code]

        company = self.company_id.sudo()._l10n_ar_get_arba_cot_company()
        recipient = self.partner_id.commercial_partner_id
        has_cuit = recipient.l10n_ar_afip_code == AR_CUIT_AFIP_CODE
        document_type = not has_cuit and COT_DOCUMENT_TYPES.get(recipient.l10n_ar_afip_code)
        departure_date = fields.Datetime.context_timestamp(
            self.with_context(tz='America/Argentina/Buenos_Aires'),
            self.l10n_ar_cot_departure_date or self.scheduled_date,
        )
        remito = [
            '02',  # TIPO_REGISTRO
            f'{emission_date:%Y%m%d}',  # FECHA_EMISION
            self._l10n_ar_get_cot_unique_code(),  # CODIGO_UNICO
            f'{departure_date:%Y%m%d}',  # FECHA_SALIDA_TRANSPORTE
            f'{departure_date:%H%M}',  # HORA_SALIDA_TRANSPORTE
            'E',  # SUJETO_GENERADOR
            '1' if recipient.l10n_ar_afip_responsibility_type_id.code == '5' else '0',  # DESTINATARIO_CONSUMIDOR_FINAL
            document_type or '',  # DESTINATARIO_TIPO_DOCUMENTO
            str(recipient._get_id_number_sanitize()) if document_type else '',  # DESTINATARIO_DOCUMENTO
            recipient.vat if has_cuit else '',  # DESTINATARIO_CUIT
            recipient.name[:50],  # DESTINATARIO_RAZON_SOCIAL
            '0',  # DESTINATARIO_TENEDOR
            *get_address(self.partner_id),  # DESTINO_DOMICILIO_CALLE to DESTINO_DOMICILIO_PROVINCIA
            '',  # PROPIO_DESTINO_DOMICILIO_CODIGO
            'SI',  # ENTREGA_DOMICILIO_ORIGEN
            company.vat,  # ORIGEN_CUIT
            company.name[:50],  # ORIGEN_RAZON_SOCIAL
            '1',  # EMISOR_TENEDOR
            *get_address(self.picking_type_id.warehouse_id.partner_id),  # ORIGEN_DOMICILIO_CALLE to ORIGEN_DOMICILIO_PROVINCIA
            self.l10n_ar_cot_carrier_id.vat,  # TRANSPORTISTA_CUIT
            '', '', '', '',  # TIPO_RECORRIDO, RECORRIDO_LOCALIDAD, RECORRIDO_CALLE, RECORRIDO_RUTA
            self.l10n_ar_cot_license_plate,  # PATENTE_VEHICULO
            '',  # PATENTE_ACOPLADO
            '1' if self.l10n_ar_cot_is_non_finished_product else '0',  # PRODUCTO_NO_TERM_DEV
            str(round(self.l10n_ar_cot_amount * 100)) if self.l10n_ar_cot_amount else '',  # IMPORTE
        ]
        products = []
        for move in self.move_ids.filtered('quantity'):
            product = move.product_id
            quantity = str(round(move.quantity_product_uom * 100))
            products.append([
                '03',  # TIPO_REGISTRO
                product.l10n_ar_arba_code,  # CODIGO_UNICO_PRODUCTO
                product.uom_id.l10n_ar_arba_unit_code,  # RENTAS_CODIGO_UNIDAD_MEDIDA
                quantity,  # CANTIDAD
                product.default_code[:25],  # PROPIO_CODIGO_PRODUCTO
                product.name[:40],  # PROPIO_DESCRIPCION_PRODUCTO
                product.uom_id.name[:20],  # PROPIO_DESCRIPCION_UNIDAD_MEDIDA
                quantity,  # CANTIDAD_AJUSTADA
            ])
        records = [['01', company.vat], remito, *products, ['04', '1']]
        return ''.join('|'.join(map(sanitize, record)) + '\n' for record in records)

    @api.model
    def _l10n_ar_get_cot_url(self, cot_env):
        """ Return the ARBA COT url based on the environment. """
        return f"https://cot{'.test' if cot_env == 'testing' else ''}.arba.gov.ar/TransporteBienes/SeguridadCliente/presentarRemitos.do"

    def _l10n_ar_send_cot_to_arba(self):
        """ Generate the COT file and send it to ARBA, return a tuple (response_content, error) where error is None on success. """
        self.ensure_one()
        company = self.company_id.sudo()._l10n_ar_get_arba_cot_company()
        emission_date = fields.Date.context_today(self.with_context(tz='America/Argentina/Buenos_Aires'))
        file_name = f'TB_{company.vat}_000000_{emission_date:%Y%m%d}_{company._l10n_ar_get_arba_cot_file_sequence_num()}.txt'
        txt_content = self._l10n_ar_get_cot_txt(emission_date).encode('ISO-8859-1', errors='replace')
        cot_env = company.l10n_ar_arba_cot_environment
        if cot_env == 'demo':
            response_content = (
                f'<TBCOMPROBANTE><cuitEmpresa>{company.vat}</cuitEmpresa><nombreArchivo>{file_name}</nombreArchivo>'
                f'<validacionesRemitos><remito><numeroUnico>{self._l10n_ar_get_cot_unique_code()}</numeroUnico>'
                f'<procesado>SI</procesado><cot>{self.id:014d}</cot></remito></validacionesRemitos></TBCOMPROBANTE>'
            ).encode()
        else:
            try:
                response = requests.post(
                    self._l10n_ar_get_cot_url(cot_env),
                    data={'user': company.vat, 'password': company.l10n_ar_arba_cit},
                    files={'file': (file_name, txt_content, 'text/plain')},
                    timeout=(10, 30),
                )
            except requests.exceptions.RequestException as error:
                _logger.exception("ARBA COT request failed for %s", self.name)
                return None, str(error)
            # The status is not checked as ARBA describes its errors in the XML body, whatever the status
            response_content = response.content

        self.message_post(
            body=self.env._("The COT file has been sent to ARBA."),
            attachments=[(file_name, txt_content)],
        )
        return response_content, None

    def _l10n_ar_process_cot_response(self, response_content):
        self.ensure_one()
        attachments = [(f'COT - {self.l10n_ar_delivery_guide_number}.xml', response_content)]
        try:
            root = etree.fromstring(response_content)
        except etree.XMLSyntaxError:
            self.l10n_ar_cot_error = self.env._("ARBA returned an invalid response.")
            self.message_post(body=self.l10n_ar_cot_error, attachments=attachments)
            return

        cot_number = root.findtext('.//remito/cot')
        if cot_number and root.findtext('.//remito/procesado') == 'SI':
            self.write({'l10n_ar_cot_number': cot_number, 'l10n_ar_cot_error': False})
            if self.company_id.sudo()._l10n_ar_get_arba_cot_company().l10n_ar_arba_cot_environment == 'demo':
                body = self.env._("Demo COT %s generated, it was not sent to ARBA.", cot_number)
            else:
                body = self.env._("COT %s generated successfully.", cot_number)
            self.message_post(body=body, attachments=attachments)
            return

        errors = [f"[{error.findtext('codigo')}] {error.findtext('descripcion')}" for error in root.iter('error')]
        if root.tag == 'TBError':
            errors.append(f"[{root.findtext('codigoError')}] {root.findtext('mensajeError')}")
        self.l10n_ar_cot_error = "\n".join(errors) or self.env._("ARBA did not return a COT number.")
        self.message_post(body=self.env._("The COT generation failed."), attachments=attachments)

    def l10n_ar_action_generate_cot(self):
        """ Send the COT file to ARBA and store the COT number, or the errors returned by ARBA. """
        self.ensure_one()
        self._l10n_ar_check_cot_data()

        try:
            self.lock_for_update(allow_referencing=True)
        except LockError:
            raise UserError(self.env._("This transfer is being processed by another operation, please try again later.")) from None
        response_content, error = self._l10n_ar_send_cot_to_arba()
        if error:
            self.l10n_ar_cot_error = self.env._("The connection with ARBA failed, please try again later.\n%s", error)
            return
        self._l10n_ar_process_cot_response(response_content)
