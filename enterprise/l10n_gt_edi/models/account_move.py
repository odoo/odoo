import logging

from lxml import etree
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import cleanup_xml_node, html2plaintext
from odoo.tools.sql import column_exists, create_column, table_exists

from .utils import _l10n_gt_edi_send_to_sat

DTE_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
_logger = logging.getLogger(__name__)

DOC_TYPE_NAME = {
    'FACT': "Factura Electrónica",
    'FCAM': "Factura Cambiaria",
    'FESP': "Factura Especial",
    'FPEQ': "Factura Electrónica para Pequeños Contribuyentes",
    'FCAP': "Factura Cambiaria de Pequeño Contribuyente",
    'NABN': "Nota de Pago Electrónica",
    'NCRE': "Nota de Crédito Electrónica",
    'NDEB': "Nota de Débito Electrónica",
}

VALID_DOC_TYPES_BY_AFFILIATION = {
    'GEN': {'FACT', 'FCAM', 'FESP', 'NABN', 'NCRE', 'NDEB'},
    'PEQ': {'FPEQ', 'FCAP', 'NABN'},
    'PEE': {'NABN'},
    'AGR': {'NABN'},
    'AGE': {'NABN'},
    'ECA': {'NABN'},
    'EXI': {'NABN'},
    'EXE': {},
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_gt_edi_document_ids = fields.One2many(
        comodel_name='l10n_gt_edi.document',
        inverse_name='invoice_id',
    )
    l10n_gt_edi_doc_type = fields.Selection(
        selection=[
            (document_type_key, f"{document_type_key} - {document_type_description}")
            for document_type_key, document_type_description in DOC_TYPE_NAME.items()
        ],
        string="GT Document Type",
        compute='_compute_l10n_gt_edi_doc_type',
        store=True,
        readonly=False,
    )
    l10n_gt_edi_available_doc_types = fields.Char(compute="_compute_l10n_gt_edi_available_doc_types")
    l10n_gt_edi_state = fields.Selection(
        selection=[
            ('invoice_sent', 'Sent'),
        ],
        string="GT Status",
        compute='_compute_from_l10n_gt_edi_document_ids',
        store=True,
        tracking=True,
    )
    l10n_gt_edi_phrase_ids = fields.Many2many(
        comodel_name='l10n_gt_edi.phrase',
        string="GT Phrases",
        compute='_compute_l10n_gt_edi_phrase_ids',
        store=True,
        readonly=False,
    )
    l10n_gt_edi_show_consignatory_partner = fields.Boolean(compute='_compute_l10n_gt_edi_show_consignatory_partner')
    l10n_gt_edi_consignatory_partner = fields.Many2one(
        comodel_name='res.partner',
        string="Consignatory Company",
        compute='_compute_l10n_gt_edi_consignatory_partner',
        store=True,
        readonly=False,
    )
    l10n_gt_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        compute='_compute_from_l10n_gt_edi_document_ids',
        store=True,
        readonly=True,
    )

    def _auto_init(self):
        """
        Create all compute-stored fields here to avoid MemoryError when initializing on large databases.
        """
        for column_name, column_type in (
            ("l10n_gt_edi_doc_type", "varchar"),
            ("l10n_gt_edi_state", "varchar"),
            ("l10n_gt_edi_consignatory_partner", "int4"),
            ("l10n_gt_edi_attachment_id", "int4"),
        ):
            if not column_exists(self.env.cr, 'account_move', column_name):
                create_column(self.env.cr, 'account_move', column_name, column_type)

        if not table_exists(self.env.cr, 'account_move_l10n_gt_edi_phrase_rel'):
            self.env.cr.execute(
                """
                CREATE TABLE account_move_l10n_gt_edi_phrase_rel (
                    account_move_id INTEGER NOT NULL,
                    l10n_gt_edi_phrase_id INTEGER NOT NULL,
                    PRIMARY KEY (account_move_id, l10n_gt_edi_phrase_id)
                );
                COMMENT ON TABLE account_move_l10n_gt_edi_phrase_rel IS 'RELATION BETWEEN account_move_id AND l10n_gt_edi_phrase_id';
                CREATE INDEX ON account_move_l10n_gt_edi_phrase_rel (l10n_gt_edi_phrase_id, account_move_id);
                """
            )

        return super()._auto_init()

    ################################################################################
    # Compute Methods
    ################################################################################

    @api.depends('l10n_gt_edi_state')
    def _compute_show_reset_to_draft_button(self):
        """
        Prevent user to reset move to draft when a successful response has been received.
        """
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_gt_edi_state == 'invoice_sent':
                move.show_reset_to_draft_button = False

    @api.depends('l10n_gt_edi_document_ids')
    def _compute_from_l10n_gt_edi_document_ids(self):
        self.l10n_gt_edi_state = False
        self.l10n_gt_edi_attachment_id = False

        for move in self:
            for document in move.l10n_gt_edi_document_ids.sorted():
                if document.state == 'invoice_sent':
                    move.l10n_gt_edi_state = document.state
                    move.l10n_gt_edi_attachment_id = document.attachment_id
                    break

    @api.depends('country_code', 'move_type', 'debit_origin_id')
    def _compute_l10n_gt_edi_available_doc_types(self):
        """
        Ensure that the GT Document Type only displays the suitable options based on the move type.
        """
        for move in self:
            available_types = []
            if move.country_code == 'GT':
                if move.debit_origin_id:
                    available_types.append('NDEB')
                elif move.move_type in ('out_refund', 'in_refund'):
                    available_types.append('NCRE')
                elif move.move_type in ('out_invoice', 'out_receipt', 'in_invoice', 'in_receipt'):
                    available_types.extend(('FACT', 'FCAM', 'FPEQ', 'FCAP'))

                if not move.debit_origin_id and move.move_type in ('in_invoice', 'in_receipt'):
                    available_types.extend(('NABN', 'FESP'))

            final_available_types = [
                doc_type
                for doc_type in available_types
                if doc_type in VALID_DOC_TYPES_BY_AFFILIATION.get(move.company_id.l10n_gt_edi_vat_affiliation, {})
            ]
            move.l10n_gt_edi_available_doc_types = ','.join(final_available_types)

    @api.depends('l10n_gt_edi_available_doc_types')
    def _compute_l10n_gt_edi_doc_type(self):
        for move in self:
            if move.l10n_gt_edi_doc_type:
                move.l10n_gt_edi_doc_type = move.l10n_gt_edi_doc_type
            elif move.country_code == 'GT' and move.l10n_gt_edi_available_doc_types:
                move.l10n_gt_edi_doc_type = move.l10n_gt_edi_available_doc_types.split(',')[0]
            else:
                move.l10n_gt_edi_doc_type = False

    @api.depends('commercial_partner_id', 'l10n_gt_edi_doc_type')
    def _compute_l10n_gt_edi_phrase_ids(self):
        for move in self:
            if move.country_code == 'GT' and move.commercial_partner_id and move.l10n_gt_edi_doc_type not in ('FESP', 'NABN'):
                if move.state == 'draft':
                    move.l10n_gt_edi_phrase_ids = (
                        move.l10n_gt_edi_phrase_ids +
                        move.company_id.l10n_gt_edi_phrase_ids +
                        move.commercial_partner_id.l10n_gt_edi_phrase_ids
                    )
                else:
                    move.l10n_gt_edi_phrase_ids = move.l10n_gt_edi_phrase_ids
            else:
                move.l10n_gt_edi_phrase_ids = False

    @api.depends('country_code', 'commercial_partner_id')
    def _compute_l10n_gt_edi_show_consignatory_partner(self):
        for move in self:
            move.l10n_gt_edi_show_consignatory_partner = all((
                move.country_code == 'GT',
                move.commercial_partner_id.country_code not in ('GT', False),
            ))

    @api.depends('l10n_gt_edi_show_consignatory_partner')
    def _compute_l10n_gt_edi_consignatory_partner(self):
        for move in self:
            move.l10n_gt_edi_consignatory_partner = (
                move.l10n_gt_edi_show_consignatory_partner
                and move.l10n_gt_edi_consignatory_partner
                or move.company_id.partner_id
            )

    ################################################################################
    # Guatemalan Document Shorthands & Helpers
    ################################################################################

    def _l10n_gt_edi_create_document_invoice_sent(self, values: dict):
        """ Shorthand for creating a ``l10n_gt_edi.document`` of state ``invoice_sent``.
        This attachment will be saved on the move, hence the reference to the move `_name` and `id`
        on the attachment's `res_model` and `res_id`.
        :param values: dictionary of the success result, containing 'uuid', 'series', 'serial_number', 'certification_date'
        :return: ``l10n_gt_edi.document`` object """
        self.ensure_one()
        document = self.env['l10n_gt_edi.document'].sudo().create({
            'invoice_id': self.id,
            'state': 'invoice_sent',
            'uuid': values['uuid'],
            'series': values['series'],
            'serial_number': values['serial_number'],
            'certification_date': values['certification_date'],
        })
        document.attachment_id = self.env['ir.attachment'].sudo().create([{
            'name': self._l10n_gt_edi_get_sat_xml_name(),
            'res_model': self._name,
            'res_id': self.id,
            'raw': values['certificate'],
            'type': 'binary',
            'mimetype': 'application/xml',
        }])

    def _l10n_gt_edi_create_document_invoice_sending_failed(self, values: dict):
        """ Shorthand for creating a ``l10n_gt_edi.document`` of state ``invoice_sending_failed``.
        :param values: dictionary with format of { 'errors': <list[str]>, 'xml': <optional/str: for attachment> }
        :return: ``l10n_gt_edi.document`` object """
        self.ensure_one()
        message_title = _("Error when sending the XML to the SAT")
        document = self.env['l10n_gt_edi.document'].sudo().create({
            'invoice_id': self.id,
            'state': 'invoice_sending_failed',
            'message': message_title + ":\n" + '\n'.join(values['errors'])
        })
        if values.get('xml'):
            document.attachment_id = self.env['ir.attachment'].sudo().create([{
                'name': f"SAT_failed_{self._l10n_gt_edi_get_name()}.xml",
                'res_model': document._name,
                'res_id': document.id,
                'raw': values['xml'],
                'type': 'binary',
                'mimetype': 'application/xml',
            }])

    ################################################################################
    # Helpers
    ################################################################################

    def _l10n_gt_edi_get_name(self):
        self.ensure_one()
        return self.name.replace('/', '_')

    def _l10n_gt_edi_get_sat_xml_name(self):
        self.ensure_one()
        return f"SAT_certificate_{self._l10n_gt_edi_get_name()}.xml"

    def _get_name_invoice_report(self):
        # EXTENDS account
        self.ensure_one()
        if self.l10n_gt_edi_state == 'invoice_sent':
            return 'l10n_gt_edi.report_invoice_document'
        return super()._get_name_invoice_report()

    def _l10n_gt_edi_get_extra_invoice_report_values(self):
        self.ensure_one()
        if self.l10n_gt_edi_state != 'invoice_sent':
            return {}

        current_company = self.company_id
        sudo_root_company = current_company.sudo().parent_ids.filtered('partner_id.vat')[-1:] or current_company.sudo().root_id
        document = self.l10n_gt_edi_document_ids.sorted()[0]
        sat_url_params = urlencode({
            'tipo': 'autorizacion',
            'numero': document.uuid,
            'emisor': sudo_root_company.vat,
            'receptor': self.commercial_partner_id.vat,
            'monto': self.amount_total,
        })
        barcode_params = urlencode({
            'barcode_type': 'QR',
            'value': f"https://felpub.c.sat.gob.gt/verificador-web/publico/vistas/verificacionDte.jsf?{sat_url_params}",
            'width': 120,
            'height': 120,
        })

        report_values = {
            'total_lines': len(self.invoice_line_ids),
            'barcode_src': f'/report/barcode/?{barcode_params}',
            'document_name': DOC_TYPE_NAME[self.l10n_gt_edi_doc_type],
            'uuid': document.uuid,
            'series': document.series,
            'serial_number': document.serial_number,
            'certification_date': document.certification_date,
            'company_name': current_company.l10n_gt_edi_legal_name,
            'company_vat': sudo_root_company.vat,
            'phrases': self.l10n_gt_edi_phrase_ids.mapped('pdf_message'),
            'have_exportacion': self.l10n_gt_edi_doc_type == 'FACT' and self.commercial_partner_id.country_code != 'GT',
            'have_referencias': self.l10n_gt_edi_doc_type in ('NCRE', 'NDEB'),
            'have_cambiaria': self.l10n_gt_edi_doc_type in ('FCAM', 'FCAP'),
            'is_especial_fectura': self.l10n_gt_edi_doc_type == 'FESP',
        }
        if report_values['have_exportacion']:
            self._l10n_gt_edi_add_export_values(report_values)
        if report_values['have_referencias']:
            self._l10n_gt_edi_add_reference_values(report_values)
        if report_values['have_cambiaria']:
            self._l10n_gt_edi_add_payment_values(report_values)
        if report_values['is_especial_fectura']:
            self._l10n_gt_edi_add_withholding_values(report_values)
        return report_values

    def _get_l10n_gt_withhold_tax_groups_id(self):
        ChartTemplate = self.env['account.chart.template'].with_company(self.company_id)
        tax_group_iva_withhold = ChartTemplate.ref('tax_group_iva_withhold_12', raise_if_not_found=False)
        tax_group_isr_withhold = ChartTemplate.ref('tax_group_isr_withhold_5', raise_if_not_found=False)
        return (
            {
                'iva_withhold': tax_group_iva_withhold.id,
                'isr_withhold': tax_group_isr_withhold.id,
            }
            if tax_group_iva_withhold and tax_group_isr_withhold
            else {}
        )

    ################################################################################
    # Alerts & Errors Helper
    ################################################################################

    def _l10n_gt_edi_get_alerts(self):
        """
        Compute all possible common errors before sending the XML to the SAT
        """
        self.ensure_one()
        alerts = {}
        current_company = self.company_id
        sudo_root_company = current_company.sudo().parent_ids.filtered('partner_id.vat')[-1:] or current_company.sudo().root_id
        partner_is_cf = self.commercial_partner_id == self.env.ref('l10n_gt_edi.final_consumer', raise_if_not_found=False)
        partner_identification = self.commercial_partner_id.l10n_latam_identification_type_id
        error_action_partner = {
            'action_text': _("View Partner"),
            'action': self.commercial_partner_id._get_records_action(name=_("Partner")),
        }
        error_action_partner_company_current = {
            'action_text': _("View Current Company Contact"),
            'action': current_company.partner_id._get_records_action(name=_("Current Company Contact")),
        }
        error_action_partner_company_root = {
            'action_text': _("View Root Company Contact"),
            'action': sudo_root_company.partner_id._get_records_action(name=_("Root Company Contact")),
        }
        error_action_company_current = {
            'action_text': _("View Current Company"),
            'action': current_company._get_records_action(name=_("Current Company")),
        }
        error_action_gt_settings = {
            'action_text': _("View Settings"),
            'action': {
                'name': _("Settings"),
                'type': 'ir.actions.act_url',
                'target': 'self',
                'url': '/odoo/settings#l10n_gt_edi_settings',
            },
        }

        if not sudo_root_company.vat:
            alerts['l10n_gt_edi_missing_vat'] = {'message': _("Missing VAT on company %s", sudo_root_company.name)}
        if self.l10n_gt_edi_show_consignatory_partner and not self.l10n_gt_edi_consignatory_partner:
            alerts['l10n_gt_edi_missing_consignatory'] = {'message': _("Missing Consignatory Company")}
        if self.l10n_gt_edi_show_consignatory_partner and self.l10n_gt_edi_consignatory_partner and not self.l10n_gt_edi_consignatory_partner.l10n_gt_edi_consignatory_code:
            alerts['l10n_gt_edi_missing_consignatory_code'] = {
                'message': _("Missing Consignatory Code on partner %s", self.l10n_gt_edi_consignatory_partner.name),
                'action_text': _("View Consignatory Company"),
                'action': self.l10n_gt_edi_consignatory_partner._get_records_action(name=_("Consignatory Company")),
            }

        if all((
            not partner_is_cf,                                # Real partner
            self.commercial_partner_id.country_code == 'GT',  # From Guatemala
            self.commercial_partner_id.vat,                   # With VAT
            partner_identification.country_id.code != 'GT',   # That has non-GT LATAM id type (not NIT or CUI)
        )):
            alerts['l10n_gt_edi_invalid_id_type'] = {
                'message': _("Guatemalan customer must have the LATAM identification type of either NIT or CUI"),
                **error_action_partner,
            }

        # When IDReceptor="CF" is used (on CF or partners without VAT), the total amount of the invoice must be below 2500 GTQ
        if not self.commercial_partner_id.vat and self.amount_total >= 2500:
            if partner_is_cf:
                additional_message = _("Please replace Consumidor Final with a real partner and VAT number.")
            else:
                additional_message = _("Please add the VAT on partner %s.", self.commercial_partner_id.name)
            message_title = _("The total amount of the invoice exceeds the limit allowed for partner without VAT.")
            alerts['l10n_gt_edi_missing_vat'] = {
                'message': f"{message_title} {additional_message}",
                **error_action_partner,
            }

        if not self.l10n_gt_edi_doc_type:
            alerts['l10n_gt_edi_missing_vat'] = {'message': _("Missing GT Document Type")}
        if not self.l10n_gt_edi_phrase_ids and self.l10n_gt_edi_doc_type not in ('FESP', 'NABN'):
            alerts['l10n_gt_edi_missing_vat'] = {'message': _("Missing GT Phrases")}
        if not sudo_root_company.l10n_gt_edi_phrase_ids:
            alerts['l10n_gt_edi_missing_vat'] = {
                'message': _("Company must have at least one phrase"),
                **error_action_partner_company_root,
            }
        if not current_company.l10n_gt_edi_establishment_code:
            alerts['l10n_gt_edi_missing_vat'] = {
                'message': _("Missing GT Establishment Code on the Journal"),
                **error_action_company_current,
            }

        if sudo_root_company.l10n_gt_edi_service_provider in ('test', 'production'):
            if not sudo_root_company.l10n_gt_edi_ws_prefix:
                alerts['l10n_gt_edi_ws_prefix_missing'] = {
                    'message': _("Missing Infile Username Credential. Please configure it in the settings"),
                    **error_action_gt_settings,
                }
            if not sudo_root_company.l10n_gt_edi_infile_token:
                alerts['l10n_gt_edi_infile_token_missing'] = {
                    'message': _("Missing Infile Token Credential. Please configure it in the settings"),
                    **error_action_gt_settings,
                }
            if not sudo_root_company.l10n_gt_edi_infile_key:
                alerts['l10n_gt_edi_infile_key_missing'] = {
                    'l10n_gt_edi_settingsmessage': _("Missing Infile Key Credential. Please configure it in the settings"),
                    **error_action_gt_settings,
                }

        # Any missing address fields on the company should raise error before sending
        if not all((
            current_company.street,
            current_company.zip,
            current_company.city,
            current_company.state_id,
        )):
            alerts['l10n_gt_edi_missing_address_company'] = {
                'message': _("Company is missing some of the following required address fields: Street, Zip, City, State"),
                **error_action_partner_company_current,
            }

        if self.l10n_gt_edi_doc_type == 'NCRE':
            if not self.reversed_entry_id:
                alerts['l10n_gt_edi_missing_ncre_entry'] = {'message': _("Credit Notes must have a linked invoice")}
            if self.reversed_entry_id and self.reversed_entry_id.l10n_gt_edi_state != 'invoice_sent':
                alerts['l10n_gt_edi_invalid_ncre_entry'] = {'message': _("Credit Notes linked invoice must have been successfully sent to the SAT")}
            if not self.ref:
                alerts['l10n_gt_edi_missing_ncre_ref'] = {'message': _("Credit Notes must contain references")}
        elif self.l10n_gt_edi_doc_type == 'NDEB':
            if not self.debit_origin_id:
                alerts['l10n_gt_edi_missing_ndeb_entry'] = {'message': _("Debit Notes must have a linked invoice")}
            if self.debit_origin_id and self.debit_origin_id.l10n_gt_edi_state != 'invoice_sent':
                alerts['l10n_gt_edi_invalid_ndeb_entry'] = {'message': _("Debit Notes linked invoice must have been successfully sent to the SAT")}
            if not self.ref:
                alerts['l10n_gt_edi_missing_ndeb_ref'] = {'message': _("Debit Notes must contain references")}

        if self.l10n_gt_edi_doc_type in ('FCAM', 'FCAP') and (not self.invoice_date_due or self.invoice_date_due == self.invoice_date):
            alerts['l10n_gt_edi_pay_immediate_must_fact'] = {'message': _(
                "%s is only for credit invoices. It can't be used when the payment term is immediate.",
                self.l10n_gt_edi_doc_type,
            )}

        if self.l10n_gt_edi_doc_type == 'FESP':
            withhold_tax_group_ids = self._get_l10n_gt_withhold_tax_groups_id().values()
            if withhold_tax_group_ids and any(
                not all(tax_group_id in line.tax_ids.tax_group_id.ids for tax_group_id in withhold_tax_group_ids)
                for line in self.invoice_line_ids
                if line.display_type == 'product'
            ):
                alerts['l10n_gt_edi_missing_tax_on_fesp'] = {
                    'message': _(
                        "Each product line must have both VAT Withholding and ISR Withholding taxes "
                        "in order to send it with FESP"
                    )
                }

        if self.l10n_gt_edi_doc_type in ('FPEQ', 'FCAP', 'NABN'):
            if any(line.tax_ids for line in self.invoice_line_ids if line.display_type == 'product'):
                alerts['l10n_gt_edi_forbidden_tax'] = {'message': _(
                    "All invoice lines must not have any tax for document type %s", self.l10n_gt_edi_doc_type)}
        elif self.l10n_gt_edi_doc_type:  # ∈ {'FACT', 'FCAM', 'NCRE', 'NDEB'}
            if any(not line.tax_ids for line in self.invoice_line_ids if line.display_type == 'product'):
                alerts['l10n_gt_edi_missing_tax'] = {'message': _(
                    "All invoice lines must have taxes for document type %s", self.l10n_gt_edi_doc_type)}

        if all((
            self.commercial_partner_id.country_code != 'GT',  # Export invoices (uses Exportacion complemento)
            'consu' in self.invoice_line_ids.product_id.mapped('type')  # Have product lines of type goods
            or all(                                                     # Or have product combo lines where every item inside it is goods product
                combo_child_product.type == 'consu'
                for combo_product in self.invoice_line_ids.product_id.filtered(lambda p: p.type == 'combo')
                for combo_child_product in combo_product.combo_ids.combo_item_ids.product_id
            ),
            not self.invoice_incoterm_id,  # Without Incoterm code
        )):
            alerts['l10n_gt_edi_missing_incoterm'] = {'message': _("Incoterm is required on export invoice with goods product but it's currently missing")}

        return alerts

    def _l10n_gt_edi_get_pre_send_errors(self):
        self.ensure_one()
        alerts = self._l10n_gt_edi_get_alerts()
        errors = [alert_vals['message'] for alert_vals in alerts.values()]
        return errors

    ################################################################################
    # Guatemalan EDI Business Flow
    ################################################################################
    def _l10n_gt_total_grouping_function(self, base_line, tax_data):
        withhold_tax_groups = self._get_l10n_gt_withhold_tax_groups_id().values()
        if not tax_data or not withhold_tax_groups:
            return None
        tax = tax_data['tax']
        is_withhold = (
            self.l10n_gt_edi_doc_type == 'FESP'
            and tax.tax_group_id.id in withhold_tax_groups
        )
        return {
            'tax_group_id': tax.tax_group_id.id,
            'is_withhold': is_withhold,
        }

    def _l10n_gt_edi_add_base_values(self, gt_values: dict):
        self.ensure_one()
        items = []
        total_impuestos = []
        base_lines, _tax_lines = self._get_rounded_base_and_tax_lines()
        AccountTax = self.env['account.tax']
        withhold_tax_groups = self._get_l10n_gt_withhold_tax_groups_id().values()

        def need_tax_data_to_be_reported(tax_data):
            if not tax_data or not withhold_tax_groups:
                return False

            tax = tax_data['tax']
            return (
                not self.l10n_gt_edi_doc_type in ('FPEQ', 'FCAP', 'NABN')
                and not (
                    self.l10n_gt_edi_doc_type == 'FESP'
                    and tax.tax_group_id.id in withhold_tax_groups
                )
            )

        def tax_grouping_function(_arg_base_line, arg_tax_data):
            if not need_tax_data_to_be_reported(arg_tax_data):
                return {}

            tax = arg_tax_data['tax']
            return {
                'nombre_corto': tax.l10n_gt_edi_short_name,
                'codigo_unidad_gravable': tax.l10n_gt_edi_taxable_unit_code,
                'is_petroleo': tax.l10n_gt_edi_short_name == 'PETROLEO'
            }

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, tax_grouping_function)
        for item_no, (base_line, aggregated_values) in enumerate(base_lines_aggregated_values, start=1):
            line = base_line['record']
            is_goods_product = (
                line.product_id.type == 'consu' or
                line.product_id.type == 'combo' and
                set(line.product_id.combo_ids.combo_item_ids.product_id.mapped('type')) == {'consu'}
            )
            discount = base_line['discount']
            price_unit = base_line['price_unit']
            quantity = base_line['quantity']
            tax_details = base_line['tax_details']
            price_total = (
                tax_details['raw_total_excluded_currency']
                + sum(
                    tax_data['raw_tax_amount_currency']
                    for tax_data in tax_details['taxes_data']
                    if tax_data['tax'].tax_group_id.id not in withhold_tax_groups
                )
                if self.l10n_gt_edi_doc_type == 'FESP' and withhold_tax_groups
                else tax_details['raw_total_included_currency']
            )

            if discount == 100.0:
                gross_price_total_before_discount = price_unit * quantity
            else:
                gross_price_total_before_discount = price_total / (1 - discount / 100.0)

            discount_amount = gross_price_total_before_discount - price_total
            if quantity:
                gross_price_unit = gross_price_total_before_discount / quantity
            else:
                gross_price_unit = price_unit

            items.append({
                'numero_linea': item_no,
                'bien_o_servicio': "B" if is_goods_product else "S",
                'cantidad': quantity,
                'descripcion': line.name.replace('\n', ' '),
                'precio_unitario': f'{gross_price_unit:.10f}',
                'precio': f'{gross_price_total_before_discount:.10f}',
                'descuento': f'{discount_amount:.10f}',
                'total': f'{price_total:.10f}',
                'impuestos': [
                    {
                        'nombre_corto': grouping_key['nombre_corto'],
                        'codigo_unidad_gravable': grouping_key['codigo_unidad_gravable'],
                        'monto_impuesto': f"{values['tax_amount_currency']:.10f}",
                        'monto_gravable': f"{values['base_amount_currency']:.10f}" if not grouping_key['is_petroleo'] else None,
                        'cantidad_unidadades_gravables': base_line['quantity'] if grouping_key['is_petroleo'] else None,
                    } for grouping_key, values in aggregated_values.items() if grouping_key
                ],
            })

        def global_tax_grouping_function(base_line, tax_data):
            if not need_tax_data_to_be_reported(tax_data):
                return {}
            return {'nombre_corto': tax_data['tax'].l10n_gt_edi_short_name}

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, global_tax_grouping_function)
        aggregated_tax_details = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in aggregated_tax_details.items():
            if not grouping_key:
                continue
            total_impuestos.append({
                'nombre_corto': grouping_key['nombre_corto'],
                'total_monto_impuesto': f"{values['tax_amount_currency']:.10f}",
            })

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, lambda base_line, tax_data: True)
        aggregated_tax_details = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        total_base = sum(values['base_amount_currency'] for values in aggregated_tax_details.values())

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, self._l10n_gt_total_grouping_function)
        aggregated_tax_details = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        grand_total = total_base + sum(
            values['tax_amount_currency']
            for grouping_key, values in aggregated_tax_details.items()
            if grouping_key and not grouping_key['is_withhold']
        )

        # Emisor & Receptor identification fields
        current_company = self.company_id
        sudo_root_company = current_company.sudo().parent_ids.filtered('partner_id.vat')[-1:] or current_company.sudo().root_id
        partner_uses_cui = self.commercial_partner_id.l10n_latam_identification_type_id == self.env.ref('l10n_gt_edi.it_cui', raise_if_not_found=False)
        partner_is_final_consumer = self.commercial_partner_id == self.env.ref('l10n_gt_edi.final_consumer', raise_if_not_found=False)
        partner_is_guatemalan = self.commercial_partner_id.country_code == 'GT'

        receptor_tipo_especial = None
        receptor_id = (self.commercial_partner_id.vat or '').replace('-', '')
        if partner_is_guatemalan and partner_uses_cui:
            receptor_tipo_especial = "CUI"
        if not partner_is_guatemalan:
            receptor_tipo_especial = "EXT"
        if partner_is_final_consumer or not receptor_id:
            receptor_id = "CF"
            receptor_tipo_especial = None

        gt_values.update({
            'dte_tipo': self.l10n_gt_edi_doc_type,
            'dte_exp': 'SI' if self.commercial_partner_id.country_code != 'GT' else None,
            'dte_fecha': self.invoice_date.strftime(DTE_DATE_FORMAT),
            'dte_codigo_moneda': self.currency_id.name,
            'emisor_nit': (sudo_root_company.vat or '').replace('-', ''),
            'emisor_nombre': current_company.l10n_gt_edi_legal_name,
            'emisor_codigo_establecimiento': current_company.l10n_gt_edi_establishment_code,
            'emisor_nombre_comercial': current_company.partner_id.name,
            'emisor_afiliacion_iva': sudo_root_company.l10n_gt_edi_vat_affiliation,
            'emisor_direccion_direccion': sudo_root_company.street,
            'emisor_direccion_codigo_postal': sudo_root_company.zip,
            'emisor_direccion_municipio': sudo_root_company.city,
            'emisor_direccion_departamento': sudo_root_company.state_id.name,
            'emisor_direccion_pais': sudo_root_company.country_code,
            'receptor_id': receptor_id,
            'receptor_tipo_especial': receptor_tipo_especial,
            'receptor_nombre': self.commercial_partner_id.name,
            'receptor_direccion_direccion': self.commercial_partner_id.street,
            'receptor_direccion_codigo_postal': self.commercial_partner_id.zip,
            'receptor_direccion_municipio': self.commercial_partner_id.city,
            'receptor_direccion_departamento': self.commercial_partner_id.state_id.name,
            'receptor_direccion_pais': self.commercial_partner_id.country_code,
            'receptor_direccion_show': all(
                self.commercial_partner_id[address_field]
                for address_field in ('street', 'zip', 'city', 'state_id', 'country_code')
            ),
            'frases': [
                {
                    'tipo_frase': phrase.phrase_type,
                    'codigo_escenario': phrase.scenario_code,
                }
                for phrase in self.l10n_gt_edi_phrase_ids
            ],
            'items': items,
            'total_impuestos': total_impuestos,
            'gran_total': f"{grand_total:.10f}",
            'have_exportacion': self.l10n_gt_edi_doc_type == 'FACT' and not partner_is_guatemalan,
            'have_referencias': self.l10n_gt_edi_doc_type in ('NCRE', 'NDEB'),
            'have_cambiaria': self.l10n_gt_edi_doc_type in ('FCAM', 'FCAP'),
            'is_especial_fectura': self.l10n_gt_edi_doc_type == 'FESP',
            'skip_phrases': (
                self.l10n_gt_edi_doc_type == 'NABN'
                or (
                    self.l10n_gt_edi_doc_type == 'FESP'
                    and not self.l10n_gt_edi_phrase_ids
                )
            ),
            'narration': html2plaintext(self.narration),
        })

    def _l10n_gt_edi_add_export_values(self, gt_values: dict):
        self.ensure_one()
        gt_values.update({
            'exportacion_nombre_consignatario_o_destinatario': self.l10n_gt_edi_consignatory_partner.name[:70],
            'exportacion_direccion_consignatario_o_destinatario':
                self.l10n_gt_edi_consignatory_partner._display_address(without_company=True).replace('\n', ' - ')[:70],
            'exportacion_codigo_consignatario_o_destinatario': self.l10n_gt_edi_consignatory_partner.l10n_gt_edi_consignatory_code,
            'exportacion_otra_referencia': self.l10n_gt_edi_consignatory_partner.ref or "N/A",
            'exportacion_incoterm': 'consu' in self.invoice_line_ids.product_id.mapped('type') and self.invoice_incoterm_id.code,
        })

    def _l10n_gt_edi_add_reference_values(self, gt_values: dict):
        self.ensure_one()
        reference_move = self.reversed_entry_id if self.l10n_gt_edi_doc_type == 'NCRE' else self.debit_origin_id
        original_document = reference_move.l10n_gt_edi_document_ids.sorted()[0]  # guaranteed to be an `invoice_sent` document
        gt_values.update({
            'referencias_motivo_ajuste': self.ref,
            'referencias_fecha_emision_documento_origen': original_document.datetime.astimezone(ZoneInfo("America/Guatemala")).strftime("%Y-%m-%d"),
            'referencias_numero_autorizacion_documento_origen': original_document.uuid,
            'referencias_numero_documento_origen': original_document.serial_number,
            'referencias_serie_documento_origen': original_document.series,
        })

    def _l10n_gt_edi_add_payment_values(self, gt_values: dict):
        self.ensure_one()
        gt_values['abonos'] = []
        payment_terms = self.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        for numero_abono, payment_term_line in enumerate(payment_terms, start=1):
            gt_values['abonos'].append({
                'numero_abono': numero_abono,
                'fecha_vencimiento': payment_term_line.payment_date.strftime("%Y-%m-%d"),
                'monto_abono': f"{payment_term_line.amount_currency:.10f}",
            })

    def _l10n_gt_edi_add_withholding_values(self, gt_values: dict):
        self.ensure_one()
        withhold_group_ids = self._get_l10n_gt_withhold_tax_groups_id()
        gt_values['retencion_gran_total'] = float(gt_values['gran_total'])

        base_lines, _tax_lines = self._get_rounded_base_and_tax_lines()
        base_lines_aggregated_values = self.env['account.tax']._aggregate_base_lines_tax_details(base_lines, self._l10n_gt_total_grouping_function)
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)

        for group_key, values in aggregated_tax_details.items():
            if group_key and group_key['is_withhold']:
                if withhold_group_ids['iva_withhold'] == group_key['tax_group_id']:
                    gt_values['retencion_iva'] = -values['tax_amount']
                elif withhold_group_ids['isr_withhold'] == group_key['tax_group_id']:
                    gt_values['retencion_isr'] = -values['tax_amount']

                gt_values['retencion_gran_total'] += values['tax_amount']

    def _l10n_gt_edi_try_send(self):
        """
        Try to generate and send the CFDI for the current invoice.
        """
        self.ensure_one()

        # Lock the invoice to be sent
        self.env['res.company']._with_locked_records(self)

        # Pre-send validation
        if errors := self._l10n_gt_edi_get_pre_send_errors():
            self._l10n_gt_edi_create_document_invoice_sending_failed({'errors': errors})
            return

        # Construct the XML
        gt_values = {}
        self._l10n_gt_edi_add_base_values(gt_values)
        if gt_values['have_exportacion']:
            self._l10n_gt_edi_add_export_values(gt_values)  # FACT export invoices (to foreigner)
        if gt_values['have_referencias']:
            self._l10n_gt_edi_add_reference_values(gt_values)  # credit/debit note (NCRE/NDEB)
        if gt_values['have_cambiaria']:
            self._l10n_gt_edi_add_payment_values(gt_values)  # payment values (Abono)
        if gt_values['is_especial_fectura']:
            self._l10n_gt_edi_add_withholding_values(gt_values)  # FESP invoices

        xml_data = self.env['ir.qweb']._render('l10n_gt_edi.SAT', gt_values)
        xml_data = etree.tostring(cleanup_xml_node(xml_data, remove_blank_nodes=False), pretty_print=True, encoding='unicode')
        sudo_root_company = self.company_id.sudo().parent_ids.filtered('partner_id.vat')[-1:] or self.company_id.sudo().root_id

        # Send the XML to Infile
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        result = _l10n_gt_edi_send_to_sat(
            company=sudo_root_company,
            xml_data=xml_data,
            identification_key=f"{db_uuid}_{self._l10n_gt_edi_get_name()}",
        )

        # Remove all previous error documents
        self.l10n_gt_edi_document_ids.filtered(lambda d: d.state == 'invoice_sending_failed').unlink()

        # Create Error/Successful Document, and commit it to database
        if 'errors' in result:
            self._l10n_gt_edi_create_document_invoice_sending_failed({**result, 'xml': xml_data})
        else:  # Sent successfully
            self._l10n_gt_edi_create_document_invoice_sent(result)
            self.message_post(body=_("Successfully sent the XML to the SAT"), attachment_ids=self.l10n_gt_edi_attachment_id.ids)
            if sudo_root_company.l10n_gt_edi_service_provider == 'demo':
                self.message_post(body=_("This document has been successfully generated in DEMO mode. "
                                         "It is considered as accepted and it won't be sent to the SAT."))

        if self._can_commit():
            self._cr.commit()

    def l10n_gt_edi_send_bill_to_sat(self):
        self.ensure_one()
        self._l10n_gt_edi_try_send()

        gt_document = self.l10n_gt_edi_document_ids.sorted()[:1]
        if gt_document.state == 'invoice_sending_failed':
            raise UserError(gt_document.message)
