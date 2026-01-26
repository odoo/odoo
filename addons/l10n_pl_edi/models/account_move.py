import base64
import logging
from xml.dom.minidom import parseString

from stdnum.pl.nip import compact

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_repr

from odoo.addons.l10n_pl_edi.models.l10n_pl_ksef_api import KsefApiService

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pl_ksef_status = fields.Selection([
        ('to_send', 'To Send'),
        ('sent', 'Sent (In Progress)'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], string='KSeF Status', default='to_send', readonly=True, copy=False)

    l10n_pl_move_reference_number = fields.Char(string='KSeF Invoice Reference Number', readonly=True)
    l10n_pl_edi_register = fields.Boolean(related='company_id.l10n_pl_edi_register')

    l10n_pl_edi_header = fields.Html(
        help='User description of the current state, with hints to make the flow progress',
        readonly=True,
        copy=False,
    )
    l10n_pl_ksef_number = fields.Char(string='KSeF Number', readonly=True, index=True)

    def _check_mandatory_fields(self):
        errors = {}
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

    def _get_ksef_related_invoices(self):
        """
        Returns a list of related invoice numbers for ZAL and ROZ types.
        Safely checks for Sale Order links.
        """
        self.ensure_one()
        ksef_type = self._l10n_pl_edi_get_ksef_invoice_type()
        related_numbers = set()

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

    def _l10n_pl_ksef_get_xml_values(self):
        """
        Prepares a dictionary of values to be passed to the QWeb template.
        """
        self.ensure_one()

        def get_vat_country(vat):
            if not vat or vat[:2].isdecimal():
                return False
            return vat[:2].upper()

        def get_amounts_from_tag(tax_tag_string):
            if 'OSS' in tax_tag_string:
                oss_tag = self.env['account.account.tag']._get_tax_tags('OSS', self.env.ref('base.pl').id)
                return - sum(
                    self.line_ids.filtered(lambda line: any(tag in oss_tag for tag in line.tax_tag_ids) and (
                        line.tax_ids if 'Base' in tax_tag_string else not line.tax_ids
                    )).mapped('amount_currency'))
            else:
                tax_tags = self.env['account.account.tag']._get_tax_tags(tax_tag_string, self.env.ref('base.pl').id)
                return - sum(self.line_ids.filtered(lambda line: any(tag in tax_tags for tag in line.tax_tag_ids)).mapped('amount_currency'))

        def get_amounts_from_tag_in_PLN_currency(tax_group_id):
            conversion_line = self.invoice_line_ids.sorted(lambda line: abs(line.balance), reverse=True)[0] if self.invoice_line_ids else None
            conversion_rate = abs(conversion_line.balance / conversion_line.amount_currency) if self.currency_id != self.env.ref('base.PLN') and conversion_line else 1
            return get_amounts_from_tag(tax_group_id) * conversion_rate

        def compute_p_12(move_line):
            """
            Determines the KSeF tax rate code (P_12) based on the line's tax.
            Prioritizes tax amount for standard rates, and Tags/Names for special 0% cases.
            """
            if not move_line.tax_ids:
                return "zw"

            tax = move_line.tax_ids[0]

            # 1. Standard positive rates (23, 8, 5, etc.)
            if tax.amount > 0:
                return str(int(tax.amount))

            # 2. Analyze Tags and Names for 0% / Special cases
            # We combine tags and tax name to search for keywords
            tags_str = " ".join(move_line.tax_tag_ids.mapped('name')).lower()
            name_str = tax.name.lower()

            if 'wdt' in tags_str or 'wdt' in name_str:
                return "0 WDT"  # Intra-Community Supply

            elif 'eksport' in tags_str or 'export' in tags_str:
                return "0 EX"   # Export of goods

            elif 'odwrotne' in tags_str or 'oo' in name_str:
                return "oo"     # Reverse Charge

            elif 'niepodlegaj' in tags_str or 'np' in name_str:
                return "np I"   # Not subject to tax (assuming Type I as default)

            elif 'zw' in name_str or 'zwolnion' in tags_str:
                return "zw"     # Exempt

            # 3. Default for 0% (Domestic)
            # If rate is 0 and no special tag (WDT/Export) matches, it is 0 KR
            if tax.amount == 0:
                return "0 KR"

            return "zw"

        ksef_type = self._l10n_pl_edi_get_ksef_invoice_type()
        invoice_lines_vals = []
        sign = -1 if 'KOR' in ksef_type else 1

        for index, line in enumerate(self.invoice_line_ids, start=1):
            uu_id = f"odoo-line-{line.id}"
            p_12_value = compute_p_12(line)
            invoice_lines_vals.append({
                'NrWierszaFa': index,
                'UU_ID': uu_id,
                'P_7': line.name,
                'P_8A': line.product_uom_id.name or 'szt.',
                'P_8B': line.quantity * sign,
                'P_9A': float_repr(line.price_unit, 2),
                'P_11': float_repr(line.price_subtotal * sign, 2),
                'P_12': p_12_value,
            })

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
            origin_ksef_id = origin.l10n_pl_move_reference_number if origin else False

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
            'buyer': self.commercial_partner_id,
            'invoice_lines': invoice_lines_vals,
            'tax_summary_vals': tax_summary_vals,
            'float_repr': float_repr,
            'float_is_zero': float_is_zero,
            'get_vat_country': get_vat_country,
            'get_vat_number': compact,
            'get_amounts_from_tag': get_amounts_from_tag,
            'get_amounts_from_tag_in_PLN_currency': get_amounts_from_tag_in_PLN_currency,
            'invoice_type': ksef_type,
            'related_invoices': self._get_ksef_related_invoices(),
            'correction_info': correction_info,
        }

    def _l10n_pl_ksef_render_xml(self):
        """
        Renders the QWeb template, removes empty lines.
        """
        self.ensure_one()
        qweb_template = self.env.ref('l10n_pl_edi.fa3_xml_template')
        ksef_values = self._l10n_pl_ksef_get_xml_values()
        xml_content = self.env['ir.qweb']._render(qweb_template.id, ksef_values)
        xml_content = "\n".join([line for line in xml_content.splitlines() if line.strip()])
        _logger.info("Successfully rendered KSeF XML for invoice %s.", self.name)

        return xml_content

    def action_download_l10n_pl_ksef_xml(self):
        """
        This is the action called by the button.
        It generates the FA(3) XML, pretty-prints it,
        saves it as an attachment, and returns a download action.
        """
        self.ensure_one()
        xml_content_bytes = self._l10n_pl_ksef_render_xml().encode('utf-8')
        if not xml_content_bytes:
            raise UserError(self.env._("Generated XML content is empty."))

        xml_datas = base64.b64encode(xml_content_bytes).decode('utf-8')
        filename = f"FA3-{self.name.replace('/', '_')}.xml"

        # Search for an existing attachment to update it
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('name', '=', filename),
        ], limit=1)

        if not attachment:
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'res_model': 'account.move',
                'res_id': self.id,
                'datas': xml_datas,
                'description': self.env._('KSeF FA(3) Invoice XML'),
            })
        else:
            attachment.datas = xml_datas

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _get_ksef_status_mapping(self):
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

    def action_update_invoice_status(self):
        self.ensure_one()
        if not self.l10n_pl_move_reference_number:
            raise UserError(self.env._("This invoice does not have a KSeF Invoice Reference Number. It may not have been sent yet."))

        service = KsefApiService(self.company_id)
        try:
            response = service.get_invoice_status(self.l10n_pl_move_reference_number)
        except UserError as e:
            self.message_post(body=self.env._("Failed to check KSeF status: %s", str(e)))
            return

        _logger.info("KSeF status check response for move %s: %s", self.name, response)

        l10n_pl_ksef_number = response.get('ksefNumber', False)
        status_info = response.get('status', {})
        status_code = status_info.get('code')
        status_description = status_info.get('description', self.env._("No description provided."))

        mapping = self._get_ksef_status_mapping()

        if status_code in mapping:
            new_status, message = mapping[status_code]
            if status_code == 500:
                message = f"{message} {status_description}"
        else:
            new_status = self.l10n_pl_ksef_status
            message = self.env._("Received an unknown or unexpected status from KSeF (Code: %(code)s): %(description)s",
                        code=status_code,
                        description=status_description,
                        )
            _logger.warning("Unknown KSeF status code '%s' for move %s", status_code, self.name)

        self.write({
            'l10n_pl_ksef_status': new_status,
            'l10n_pl_edi_header': message,
            'l10n_pl_ksef_number': l10n_pl_ksef_number,
        })

        if message:
            self.message_post(body=message)

    def action_get_invoice_UPO(self):
        self.ensure_one()
        if not self.l10n_pl_move_reference_number:
            raise UserError(self.env._("This invoice does not have a KSeF Invoice Reference Number. It may not have been sent yet."))

        # It's good practice to only allow UPO download for accepted invoices
        if self.l10n_pl_ksef_status != 'accepted':
            raise UserError(self.env._("You can only download a UPO for an 'Accepted' invoice. Please update the status first."))

        service = KsefApiService(self.company_id)

        try:
            upo_xml_content = service.get_invoice_upo(self.l10n_pl_move_reference_number)
        except UserError as e:
            self.message_post(body=self.env._("Failed to download UPO: %s", str(e)))
            return None

        if not upo_xml_content:
            raise UserError(self.env._("The KSeF service returned empty UPO content."))

        dom = parseString(upo_xml_content)
        pretty_xml_bytes = dom.toprettyxml(indent="  ", encoding="utf-8")
        upo_datas = base64.b64encode(pretty_xml_bytes)
        _logger.info("Successfully pretty-printed UPO XML for %s", self.name)

        filename = f"UPO-{self.name.replace('/', '_')}.xml"

        # Search for an existing UPO attachment to avoid duplicates
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('name', '=', filename),
        ], limit=1)

        if attachment:
            attachment.datas = upo_datas
        else:
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'res_model': 'account.move',
                'res_id': self.id,
                'datas': upo_datas,
                'description': self.env._('KSeF Official Confirmation of Receipt (UPO)'),
            })

        self.message_post(
            body=self.env._("The KSeF Official Confirmation of Receipt (UPO) has been downloaded and attached."),
            attachment_ids=attachment.ids,
        )

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _cron_checks_the_polish_invoice_status(self):
        """ Get all moves that are in state sent run action_update_invoice_status on all of them """
        to_update_moves = self.env['account.move'].search([
            *self.env['account.move']._check_company_domain(self.env.company),
            ('l10n_pl_ksef_status', '=', 'sent')
        ])
        for move in to_update_moves:
            move.action_update_invoice_status()

    def button_draft(self):
        """
            When going from canceled => draft, we ensure to clear the edi fields
            so that the invoice can be resent if required.
        """
        # EXTEND account
        res = super().button_draft()
        moves = self.filtered(lambda move: move.country_code == 'PL' and move.l10n_pl_ksef_status == 'rejected')
        moves.write({
            'l10n_pl_ksef_status': 'to_send',
            'l10n_pl_ksef_number': False,
            'l10n_pl_edi_header': False,
        })
        return res

    @api.depends('l10n_pl_ksef_status')
    def _compute_show_reset_to_draft_button(self):
        """
            Invoices currently or correctly sent to the KSeF cannot be reset to draft.
        """
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            move.show_reset_to_draft_button = (
                move.l10n_pl_ksef_status not in ('sent', 'accepted')
                and move.show_reset_to_draft_button
            )
