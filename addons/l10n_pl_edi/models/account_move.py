import logging
import re
from xml.dom.minidom import parseString

from dateutil.relativedelta import relativedelta
from lxml import etree
from stdnum.pl.nip import compact

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_repr, OrderedSet

from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pl_edi_status = fields.Selection([
        ('sent', 'Sent (In Progress)'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], string='KSeF Status', readonly=True, copy=False)
    l10n_pl_edi_ref = fields.Char(string='KSeF Reference Number', readonly=True, copy=False)
    l10n_pl_edi_register = fields.Boolean(related='company_id.l10n_pl_edi_register')
    l10n_pl_edi_header = fields.Html(
        help='User description of the current state, with hints to make the flow progress',
        readonly=True,
        copy=False,
    )
    l10n_pl_edi_number = fields.Char(string='KSeF Number', readonly=True, index=True, copy=False)
    l10n_pl_edi_session_id = fields.Char(string='KSeF Session Number used for sending', copy=False, readonly=True)
    l10n_pl_edi_attachment_file = fields.Binary(copy=False, attachment=True)
    l10n_pl_edi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="KSeF Attachment",
        compute=lambda self: self._compute_linked_attachment_id('l10n_pl_edi_attachment_id', 'l10n_pl_edi_attachment_file'),
        depends=['l10n_pl_edi_attachment_file'],
    )
    l10n_pl_edi_upo_file = fields.Binary(copy=False, attachment=True)
    l10n_pl_edi_upo_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="UPO Attachment",
        compute=lambda self: self._compute_linked_attachment_id('l10n_pl_edi_upo_id', 'l10n_pl_edi_upo_file'),
        depends=['l10n_pl_edi_upo_file'],
    )

    _l10n_pl_edi_number_uniq = models.Constraint(
        'UNIQUE(l10n_pl_edi_number)',
        "The KSeF number must be unique",
    )

    def _l10n_pl_edi_check_mandatory_fields(self):
        errors = {}
        if not self:
            return errors
        company = self.company_id
        if not company.vat:
            errors['vat_missing'] = {'message': self.env._("You must have a VAT number to be able to issue e-invoices\n")}
        if not company.country_id or not company.street or not company.city:
            errors['address_problem'] = {'message': self.env._("Please complete the address of your company\n")}
        return errors

    def _l10n_pl_edi_get_ksef_invoice_type(self):
        """
        Determines the specific TRodzajFaktury for KSeF.
        """
        self.ensure_one()

        # 1. Handle Corrections (Credit Notes)
        if self.move_type == 'out_refund':
            origin_inv = self.reversed_entry_id
            if not origin_inv:
                return 'KOR'

            origin_type = origin_inv._l10n_pl_edi_get_ksef_invoice_type()
            if origin_type == 'ZAL':
                return 'KOR_ZAL'
            elif origin_type == 'ROZ':
                return 'KOR_ROZ'
            else:
                return 'KOR'

        # 2. Handle Sales Invoices
        elif self.move_type == 'out_invoice':
            has_dp_lines = any(line._get_downpayment_lines() for line in self.invoice_line_ids)

            if has_dp_lines:
                # Check for Settlement (ROZ): Contains Regular lines AND Negative Downpayment lines
                has_regular_lines = any(not line._get_downpayment_lines() for line in self.invoice_line_ids)
                has_deducted_dp = any(line._get_downpayment_lines() and float_compare(line.price_subtotal, 0.0, precision_rounding=line.currency_id.rounding) == -1 for line in self.invoice_line_ids)

                if has_regular_lines and has_deducted_dp:
                    return 'ROZ'

                # If it's not ROZ but has downpayment lines (and they are positive), it is ZAL
                return 'ZAL'

        # Default to Standard VAT invoice
        return 'VAT'

    def _l10n_pl_edi_get_related_invoices(self):
        """
        Returns a list of related invoice numbers for ZAL and ROZ types.
        Safely checks for Sale Order links.
        """
        self.ensure_one()
        ksef_type = self._l10n_pl_edi_get_ksef_invoice_type()
        related_numbers = OrderedSet()

        if ksef_type in ['ROZ', 'ZAL'] and hasattr(self.line_ids, 'sale_line_ids'):
            sale_orders = self.line_ids.sale_line_ids.order_id

            for so in sale_orders:
                previous_invoices = so.invoice_ids.filtered(
                    lambda x: x.id != self.id and x.state == 'posted'
                )

                for prev in previous_invoices:
                    # Recursively check the type of the previous invoice
                    if prev._l10n_pl_edi_get_ksef_invoice_type() == 'ZAL':
                        related_numbers.add(prev.name)

        return list(related_numbers)

    def _l10n_pl_edi_get_xml_values(self):
        """
        Prepares a dictionary of values to be passed to the QWeb template.
        """
        self.ensure_one()

        def get_vat_country(vat):
            if not vat or vat[:2].isdecimal():
                return False
            return vat[:2].upper()

        def get_address(partner):
            return re.sub(r'\n+', r' ', partner._display_address(True))

        def get_tags(code):
            return self.env['account.account.tag']._get_tax_tags(code, self.env.ref('base.pl').id)

        def get_tag_names(line):
            return line.tax_tag_ids.with_context(lang='en_US').mapped(lambda x: re.sub(r'^[+-]', r'', x.name or ''))

        def get_amounts_from_tag(tax_tag_string):
            lines = self.line_ids.filtered(lambda line: line.tax_tag_ids & get_tags(tax_tag_string))
            if 'OSS' in tax_tag_string:
                lines = lines.filtered(lambda line: line.tax_ids if 'Base' in tax_tag_string else not line.tax_ids)
            return -sum(lines.mapped('amount_currency'))

        def get_amounts_from_tag_in_PLN_currency(tax_group_id):
            conversion_line = self.invoice_line_ids.sorted(lambda line: abs(line.balance), reverse=True)[0] if self.invoice_line_ids else None
            conversion_rate = abs(conversion_line.balance / conversion_line.amount_currency) if self.currency_id != self.env.ref('base.PLN') and conversion_line else 1
            return get_amounts_from_tag(tax_group_id) * conversion_rate

        def compute_p_12(tag_names):
            """
                Determines the KSeF tax rate code (P_12) based on the line's tax.
                Prioritizes tax amount for standard rates, and Tags/Names for special 0% cases.
                Mapping was determined by looking at the Tax Report lines.
            """
            # "0 WDT": Intra-Community supply of goods (K_21)
            if 'K_21' in tag_names:
                return "0 WDT"
            # "0 EX": Export of goods in case of 0% rate for export of goods (K_22)
            if 'K_22' in tag_names:
                return "0 EX"
            # "oo": Supply of goods, taxable person acquiring (K_31)
            if 'K_31' in tag_names:
                return "oo"
            # Services included in art. 100.1.4 (K_12)
            if 'K_12' in tag_names:
                return "np II"
            # Supply of goods/services, out of the country (K_11, OSS)
            if 'K_11' in tag_names or any('OSS' in tag for tag in tag_names):
                return "np I"
            # "zw": Supply of goods/services, domestic, exempt (K_10) - must fill P_19
            if 'K_10' in tag_names:
                return "zw"
            # "0 KR": Supply of goods/services, domestic, 0% (K_13)
            if 'K_13' in tag_names:
                return "0 KR"
            # "23": Supply of goods/services, domestic, 23% (K_19)
            if 'K_19' in tag_names:
                return "23"
            # "8": Supply of goods/services, domestic, 8% (K_17)
            if 'K_17' in tag_names:
                return "8"
            # "5": Supply of goods/services, domestic, 5% (K_15)
            if 'K_17' in tag_names:
                return "8"
            # No tax? It's exempt
            return "zw"

        ksef_type = self._l10n_pl_edi_get_ksef_invoice_type()
        invoice_lines_vals = []
        sign = -1 if 'KOR' in ksef_type else 1

        invoice_lines_tag_names = [
            {tag_name for tag_name in get_tag_names(line) if tag_name}
            for line in self.invoice_line_ids
        ]
        invoice_tag_names = set().union(*invoice_lines_tag_names)

        invoice_lines_vals = [
            {
                'NrWierszaFa': index + 1,
                'UU_ID': f"odoo-line-{line.id}",
                'P_7': line.name,
                'P_8A': line.product_uom_id.name or 'szt.',
                'P_8B': line.quantity * sign,
                'P_9A': float_repr(line.price_unit, 2),
                'P_11': float_repr(line.price_subtotal * sign, 2),
                'P_12': compute_p_12(tag_names),
            }
            for index, line in enumerate(self.invoice_line_ids)
            if (tag_names := invoice_lines_tag_names[index])
        ]

        tax_summary_vals = {}

        for group in self.tax_totals.get('groups_by_subtotal', {}).values():
            tax_rate_str = str(int((group['tax_group_amount_type'] == 'percent' and group['tax_group_amount']) or 0))
            tax_summary_vals[tax_rate_str] = {
                'net': float_repr(group['tax_group_base_amount'], 2),
                'tax': float_repr(group['tax_group_amount'], 2),
            }

        correction_info = {}
        if 'KOR' in ksef_type:
            origin = self.reversed_entry_id
            origin_ksef_id = origin.l10n_pl_edi_ref if origin else False

            correction_info = {
                'PrzyczynaKorekty': self.ref or 'Korekta',
                'TypKorekty': '1',
                'NrFaKorygowanej': origin.name if origin else 'BRAK',
                'DataWystFaKorygowanej': origin.invoice_date if origin else self.invoice_date,
                'NrKSeF': origin_ksef_id,
                'NrKSeFN': '1' if not origin_ksef_id else False,
            }

        return {
            'invoice': self,
            'DataWytworzeniaFa': fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'seller': self.company_id,
            'seller_address': get_address(self.company_id.partner_id),
            'buyer': self.commercial_partner_id,
            'buyer_address': get_address(self.commercial_partner_id),
            'invoice_lines': invoice_lines_vals,
            'tax_summary_vals': tax_summary_vals,
            'float_repr': float_repr,
            'float_is_zero': float_is_zero,
            'get_vat_country': get_vat_country,
            'get_vat_number': compact,
            'get_amounts_from_tag': get_amounts_from_tag,
            'get_amounts_from_tag_in_PLN_currency': get_amounts_from_tag_in_PLN_currency,
            'invoice_type': ksef_type,
            'related_invoices': self._l10n_pl_edi_get_related_invoices(),
            'correction_info': correction_info,
            'special_transactions': {'OSS_Base', 'OSS_Tax', 'Triangular Sale'} & invoice_tag_names,
            'triangular_transaction': '1' if 'Triangular Sale' in invoice_tag_names else '2',
        }

    def _l10n_pl_edi_render_xml(self):
        """
        Renders the QWeb template, removes empty lines.
        """
        self.ensure_one()
        qweb_template = self.env.ref('l10n_pl_edi.fa3_xml_template')
        ksef_values = self._l10n_pl_edi_get_xml_values()
        xml_content = self.env['ir.qweb']._render(qweb_template.id, ksef_values)
        return "\n".join([line for line in xml_content.splitlines() if line.strip()])

    def _l10n_pl_edi_get_status_mapping(self):
        """
        Returns a dictionary mapping KSeF status codes to (odoo_status, message).
        """
        return {
            100: ('sent', self.env._("KSeF Status: Invoice accepted for further processing (Code: 100).")),
            150: ('sent', self.env._("KSeF Status: Processing in progress (Code: 150).")),
            200: ('accepted', self.env._("KSeF Status: Success (Code: 200). Invoice accepted.")),
            405: ('rejected', self.env._("KSeF Status: Rejected (Code: 405). Processing canceled.")),
            410: ('rejected', self.env._("KSeF Status: Rejected (Code: 410). Incorrect scope of permissions.")),
            415: ('rejected', self.env._("KSeF Status: Rejected (Code: 415). It is not possible to send an invoice with an attachment.")),
            430: ('rejected', self.env._("KSeF Status: Rejected (Code: 430). Invoice file verification error.")),
            435: ('rejected', self.env._("KSeF Status: Rejected (Code: 435). File decryption error.")),
            440: ('rejected', self.env._("KSeF Status: Rejected (Code: 440). Duplicate invoice.")),
            450: ('rejected', self.env._("KSeF Status: Rejected (Code: 450). Invoice document semantics verification error.")),
            500: ('rejected', self.env._("KSeF Status: Error (Code: 500). Unknown error.")),
        }

    def action_l10n_pl_edi_update_invoice_status(self):
        self.ensure_one()

        self.env['res.company']._with_locked_records(self)

        def ask_status_api():

            if not self.l10n_pl_edi_ref:
                return {
                    'l10n_pl_edi_header': self.env._("This invoice does not have a KSeF Invoice Reference Number. It may not have been sent yet."),
                }

            service = KsefApiService(self.company_id)
            try:
                response = service.get_invoice_status(
                    self.l10n_pl_edi_ref,
                    session_id=self.l10n_pl_edi_session_id,
                )
            except UserError as e:
                return {
                    'l10n_pl_edi_header': self.env._("Failed to check KSeF status: %s", e),
                }

            status_info = response.get('status', {})
            status_code = status_info.get('code')
            status_description = status_info.get('description', self.env._("No description provided."))

            if values := self._l10n_pl_edi_get_status_mapping().get(status_code):
                new_status, message = values
                if status_code == 500:
                    message = f"{message} {status_description}"
            else:
                return {
                    'l10n_pl_edi_header': self.env._(
                        "Unknown status received from KSeF (Code: %(code)s): %(description)s",
                        code=status_code,
                        description=status_description,
                    ),
                }

            return {
                'l10n_pl_edi_status': new_status,
                'l10n_pl_edi_header': message,
                'l10n_pl_edi_number': response.get('ksefNumber', False),
            }

        res = ask_status_api()

        message = res.get('l10n_pl_edi_header')
        new_status = res.get('l10n_pl_edi_status', self.l10n_pl_edi_status)
        if message and (new_status != self.l10n_pl_edi_status):
            self.with_context(no_new_invoice=True).sudo().message_post(body=message)

        self.update(res)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_l10n_pl_edi_get_invoice_UPO(self):
        self.ensure_one()
        if not self.l10n_pl_edi_ref:
            raise UserError(self.env._("This invoice does not have a KSeF Invoice Reference Number. It may not have been sent yet."))

        # It's good practice to only allow UPO download for accepted invoices
        if self.l10n_pl_edi_status != 'accepted':
            raise UserError(self.env._("You can only download a UPO for an 'Accepted' invoice. Please update the status first."))

        service = KsefApiService(self.company_id)

        try:
            upo_xml_content = service.get_invoice_upo(
                self.l10n_pl_edi_ref,
                session_id=self.l10n_pl_edi_session_id,
            )
        except UserError as e:
            self.message_post(body=self.env._("Failed to download UPO: %s", str(e)))
            return None

        if not upo_xml_content:
            raise UserError(self.env._("The KSeF service returned empty UPO content."))

        dom = parseString(upo_xml_content)
        pretty_xml_bytes = dom.toprettyxml(indent="  ", encoding="utf-8")

        if self.l10n_pl_edi_upo_id:
            self.l10n_pl_edi_upo_file.raw = pretty_xml_bytes
        else:
            self.l10n_pl_edi_upo_id = self.env['ir.attachment'].create({
                'name': f"UPO-{self.name.replace('/', '_')}.xml",
                'description': self.env._('KSeF Official Confirmation of Receipt (UPO)'),
                'type': 'binary',
                'mimetype': 'application/xml',
                'raw': pretty_xml_bytes,
                'res_id': self.id,
                'res_model': self._name,
                'res_field': 'l10n_pl_edi_upo_file',
            })

        self.sudo().with_context(no_new_invoice=True).message_post(
            body=self.env._("The KSeF Official Confirmation of Receipt (UPO) has been downloaded and attached."),
            attachment_ids=self.l10n_pl_edi_upo_id.ids,
        )

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.l10n_pl_edi_upo_id.id}?download=true',
            'target': '_blank',
        }

    def _cron_l10n_pl_edi_check_invoice_status(self):
        """get all moves that are in state sent run action_update_invoice_status on all of them"""
        to_update_moves = self.env['account.move'].search([*self.env['account.move']._check_company_domain(self.env.company), ('l10n_pl_edi_status', '=', 'sent')])
        for move in to_update_moves:
            self.env['res.company']._with_locked_records(move)
            move.action_l10n_pl_edi_update_invoice_status()

    def button_draft(self):
        """
            When going from canceled => draft, we ensure to clear the edi fields
            so that the invoice can be resent if required.
        """
        # EXTEND account
        res = super().button_draft()
        moves = self.filtered(lambda move: move.country_code == 'PL' and move.l10n_pl_edi_status == 'rejected')
        moves.write(dict.fromkeys((
            'l10n_pl_edi_status',
            'l10n_pl_edi_number',
            'l10n_pl_edi_ref',
            'l10n_pl_edi_session_id',
            'l10n_pl_edi_header',
        ), False))
        return res

    @api.depends('l10n_pl_edi_status')
    def _compute_show_reset_to_draft_button(self):
        """
            Invoices currently or correctly sent to the KSeF cannot be reset to draft.
        """
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            move.show_reset_to_draft_button = (
                move.l10n_pl_edi_status not in ('sent', 'accepted')
                and move.show_reset_to_draft_button
            )

    def _get_fields_to_detach(self):
        # EXTENDS account
        return super()._get_fields_to_detach() + ['l10n_pl_edi_attachment_file', 'l10n_pl_edi_upo_file']

    @api.model
    def l10n_pl_edi_get_ksef_bill_vals_from_xml(self, xml_content):

        p12_to_tax_xml_id_map = {
            "23": "vz_kraj_23",
            "8": "vz_kraj_8",
            "5": "vz_kraj_5",
            "0 KR": "vz_kraj_0",
            "zw": "vz_kraj_zw",
            "oo": "vz_stal",
            "0 WDT": "vz_unia",
            "np II": "vz_nabu",
            "0 EX": "vz_imp_tow",
            "np I": "vz_impu",
        }

        def parse_fa3_bill_xml(xml_content):
            root = etree.fromstring(xml_content)

            def get_value(node, xpath):
                res_node = node.find(xpath)
                return res_node.text if res_node is not None else None

            invoice_node = root.find('{*}Fa')
            vendor_node = root.find('{*}Podmiot1')

            vendor_nip = get_value(vendor_node, '{*}DaneIdentyfikacyjne/{*}NIP')
            vendor_name = get_value(vendor_node, '{*}DaneIdentyfikacyjne/{*}Nazwa')
            vendor_country = get_value(vendor_node, '{*}Adres/{*}KodKraju')

            invoice_date = get_value(invoice_node, '{*}P_1')
            invoice_date_due = get_value(invoice_node, '{*}Platnosc/{*}TerminPlatnosci/{*}Termin')
            invoice_number = get_value(invoice_node, '{*}P_2')
            currency_code = get_value(invoice_node, '{*}KodWaluty')
            move_line_nodes = invoice_node.findall("{*}FaWiersz")

            lines = [
                {
                    'name': get_value(line_node, '{*}P_7') or '/',
                    'uom_name': get_value(line_node, '{*}P_8A') or '',
                    'quantity': float(get_value(line_node, '{*}P_8B') or 0.0),
                    'price_unit': float(get_value(line_node, '{*}P_9A') or 0.0),
                    'tax_name': get_value(line_node, '{*}P_12') or '',
                }
                for line_node in move_line_nodes
            ]

            return {
                'vendor_nip': vendor_nip,
                'vendor_name': vendor_name,
                'vendor_country': vendor_country,
                'invoice_date': invoice_date,
                'invoice_date_due': invoice_date_due,
                'invoice_number': invoice_number,
                'currency_code': currency_code,
                'lines': lines,
            }

        def get_ksef_bill_vals(data):
            partner_vat_domain_vals = (data['vendor_nip'], f"{data['vendor_country']}{data['vendor_nip']}")
            partner = self.env['res.partner'].search(
                [
                    ('vat', 'in', partner_vat_domain_vals),
                    *self.env['res.partner']._check_company_domain(self.env.company),
                    '|',
                    ('country_id.code', '=', data['vendor_country']),
                    ('country_id', '=', False),
                ], limit=1,
            )
            if not partner:
                partner = self.env['res.partner'].create(
                    {
                        'name': data['vendor_name'],
                        'vat': data['vendor_nip'],
                        'country_id': self.env['res.country'].search([('code', '=', data['vendor_country'])]).id,
                    },
                )

            currency = self.env['res.currency'].search([('name', '=', data['currency_code'])], limit=1)

            move_vals = {
                'move_type': 'in_invoice',
                'partner_id': partner.id,
                'invoice_date': data['invoice_date'],
                'invoice_date_due': data['invoice_date_due'],
                'ref': data['invoice_number'],
                'currency_id': currency.id,
                'invoice_line_ids': [],
            }

            for line in data['lines']:

                tax_ids = []
                if xml_id := p12_to_tax_xml_id_map.get(line['tax_name']):
                    if tax := self.env['account.chart.template'].ref(xml_id, raise_if_not_found=False):
                        tax_ids.append(Command.set(tax.ids))
                    else:
                        raise UserError(self.env._("Purchase tax corresponding to '%s' required for the KSeF import was not found in the system.", line['tax_name']))

                move_vals['invoice_line_ids'].append(
                    Command.create(
                        {
                            'name': line['name'],
                            'quantity': line['quantity'],
                            'price_unit': line['price_unit'],
                            'tax_ids': tax_ids,
                        }
                    )
                )

            return move_vals

        return get_ksef_bill_vals(parse_fa3_bill_xml(xml_content))

    @api.model
    def _cron_l10n_pl_edi_download_bills(self):
        for company in self.env['res.company'].search([('l10n_pl_edi_access_token', '!=', False)]):
            blocking_error = self.with_company(company)._l10n_pl_edi_download_bills_from_ksef()
            if blocking_error:
                break

    @api.model
    def _l10n_pl_edi_download_bills_from_ksef(self):

        def handle_download_bills_from_ksef_error(error):
            if not (delay := error.get('retry_after')):
                raise UserError(error.get('message'))

            cron = self.env.ref('l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills')
            cron._trigger(at=fields.Datetime.now() + relativedelta(seconds=delay))
            return True

        service = KsefApiService(self.env.company)

        last_processed_move = self.search([
            ('l10n_pl_edi_number', '!=', False),
            ('move_type', '=', 'in_invoice'),
            *self._check_company_domain(self.env.company)
        ], order='invoice_date DESC', limit=1)

        if last_processed_move:
            date_from = fields.Datetime.to_datetime(last_processed_move.invoice_date)
        else:
            date_from = fields.Datetime.now() - relativedelta(months=1)

        query = {
            'subjectType': 'Subject2',
            'dateRange': {
                'from': date_from.isoformat(),
                'to': fields.Datetime.now().isoformat(),
                'dateType': 'Invoicing',
            },
        }

        # Rate Limiting of get_invoice_by_ksef_number
        #
        #     req/s  |  req/m  |  req/h
        #   -----------------------------
        #       8    |    16   |    64
        #
        # Page size shouldn't be more than 64.

        page_offset = 0
        page_size = 64

        has_more = True

        invoice_numbers = []
        blocking_error = False

        while has_more:
            response = service.query_invoice_metadata(query, page_size, page_offset)
            if response.get('error'):
                blocking_error = handle_download_bills_from_ksef_error(response['error'])
                break
            invoice_numbers.extend(invoice['ksefNumber'] for invoice in response['invoices'])
            has_more = response['hasMore']
            page_offset += 1

        already_processed = set(self.env['account.move'].search([
            ('l10n_pl_edi_number', 'in', invoice_numbers)
        ]).mapped('l10n_pl_edi_number'))

        to_process = [invoice_nr for invoice_nr in invoice_numbers if invoice_nr not in already_processed]

        bills_vals_list = []

        for invoice_nr in to_process:
            response = service.get_invoice_by_ksef_number(invoice_nr)
            if response.get('error'):
                blocking_error = handle_download_bills_from_ksef_error(response['error'])
                break
            bill_data = self.l10n_pl_edi_get_ksef_bill_vals_from_xml(response['xml_content'])
            bill_data['l10n_pl_edi_number'] = invoice_nr
            bills_vals_list.append(bill_data)

        self.create(bills_vals_list)

        return blocking_error
