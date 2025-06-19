import base64
import logging
from datetime import datetime

from odoo import models, fields
from odoo.tools import float_repr
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # == KSeF Fields ==
    ksef_status = fields.Selection([
        ('to_send', 'To Send'),
        ('sent', 'Sent (In Progress)'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], string='KSeF Status', default='to_send', readonly=True, copy=False)

    ksef_reference_number = fields.Char(string='KSeF Reference Number', readonly=True, copy=False)
    ksef_session_id = fields.Char(string='KSeF Session ID', readonly=True, copy=False, help="The session ID for the current asynchronous request.")
    ksef_last_response = fields.Text(string='KSeF Last Response', readonly=True, copy=False)

    show_fa3_button = fields.Boolean(compute="_compute_show_fa3_button")

    def _compute_show_fa3_button(self):
        for move in self:
            move.show_fa3_button = (
                    move.move_type == 'out_invoice'
                    and move.company_id.country_id.code == 'PL'
                    and move.state == 'posted'
            )

    def _l10n_pl_ksef_get_xml_values(self):
        """
        Prepares a dictionary of values to be passed to the QWeb template.
        """
        self.ensure_one()

        def format_monetary(amount):
            return float_repr(amount, 2)

        def get_address_lines(partner):
            adres_l1 = partner.street or ''
            if partner.street2:
                adres_l1 += f" {partner.street2}"
            adres_l2 = f"{partner.zip or ''} {partner.city or ''}".strip()
            return {'AdresL1': adres_l1, 'AdresL2': adres_l2}

        invoice_lines_vals = []
        for index, line in enumerate(self.invoice_line_ids.filtered(lambda l: not l.display_type), start=1):
            uu_id = f"odo-line-{line.id}"
            invoice_lines_vals.append({
                'NrWierszaFa': index,
                'UU_ID': uu_id,
                'P_7': line.name,
                'P_8A': line.product_uom_id.name or 'szt.',
                'P_8B': line.quantity,
                'P_9A': format_monetary(line.price_unit),
                'P_11': format_monetary(line.price_subtotal),
                'P_12': str(int(line.tax_ids[0].amount)) if line.tax_ids and line.tax_ids[0].amount_type == 'percent' else "zw",
            })

        tax_summary_vals = {}
        for group in self.tax_totals.get('groups_by_subtotal', {}).values():
            tax_rate_str = str(int(group['tax_group_amount_type'] == 'percent' and group['tax_group_amount'] or 0))
            tax_summary_vals[tax_rate_str] = {
                'net': format_monetary(group['tax_group_base_amount']),
                'tax': format_monetary(group['tax_group_amount']),
            }

        return {
            'invoice': self,
            'DataWytworzeniaFa': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'seller': self.company_id,
            'seller_address': get_address_lines(self.company_id.partner_id),
            'seller_contact': self.company_id.partner_id,
            'buyer': self.commercial_partner_id,
            'buyer_address': get_address_lines(self.commercial_partner_id),
            'buyer_contact': self.commercial_partner_id,
            'KodWaluty': self.currency_id.name,
            'P_1': self.invoice_date,
            'P_1M': self.company_id.city,
            'P_2': self.name,
            'P_6': self.invoice_date,
            'P_15': format_monetary(self.amount_total),
            'RodzajFaktury': 'VAT',
            'invoice_lines': invoice_lines_vals,
            'tax_summary_vals': tax_summary_vals,
        }

    def _l10n_pl_ksef_render_xml(self):
        """
        Renders the QWeb template with the invoice values to generate the XML content.
        """
        self.ensure_one()
        qweb_template = self.env.ref('l10n_pl_edi.fa3_xml_template', raise_if_not_found=True)
        ksef_values = self._l10n_pl_ksef_get_xml_values()
        xml_content = self.env['ir.qweb']._render(qweb_template.id, ksef_values)
        return xml_content

    def action_download_l10n_pl_ksef_xml(self):
        """
        This is the action called by the button. It returns an action
        that redirects the user to the download controller.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/l10n_pl_edi/download/{self.id}',
            'target': 'self'}

    # == KSeF Communication Methods ==
    def _ksef_get_api_url(self):
        """Fetches the KSeF API URL from system parameters. Falls back to the test environment."""
        if self.company_id.l10n_pl_ksef_environment == 'prod':
            return "https://ksef.mf.gov.pl/api"
        return "https://ksef-test.mf.gov.pl/api"

    def _ksef_get_session_token(self):
        token = self.company_id.l10n_pl_ksef_token
        if not token:
            raise UserError("KSeF authorization token not found. Please configure it in the company settings.")
        return token

    def action_send_to_ksef(self):
        """Main action to generate XML and send it to the KSeF API."""
        self.ensure_one()
        if not self.commercial_partner_id.vat:
            raise UserError("The buyer is missing a VAT number (NIP).")

        xml_content = self._l10n_pl_ksef_render_xml()
        _logger.info("Generated KSeF XML for invoice %s", self.name)

        api_url = self._ksef_get_api_url()
        endpoint = f"{api_url}/online/Invoice/Send"

        token = self._ksef_get_session_token()
        headers = {
            'Content-Type': 'application/octet-stream; charset=utf-8',
            'SessionToken': token,
        }
        invoice_payload = {
            "invoiceHash": {"hashSHA": {"algorithm": "SHA-256", "encoding": "Base64", "value": base64.b64encode(xml_content).decode()}},
            "invoicePayload": {"type": "plain", "invoiceBody": xml_content}
        }
