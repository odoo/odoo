from lxml import etree
from markupsafe import Markup

from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.addons.l10n_co_dian import xml_utils


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_co_dian_technical_key = fields.Char(string="Technical control key", help="Control key acquired in the DIAN portal, used to generate the CUFE")
    l10n_co_dian_provider = fields.Selection(related='company_id.l10n_co_dian_provider')

    @api.model
    def _l10n_co_dian_parse_numbering_range_node(self, root):
        """ Parse a 'NumberRangeResponse' node and returns a dictionary of the values it contains.

        :param root: lxml._Element, for instance:
            <c:NumberRangeResponse>
                <c:ResolutionNumber>18760000001</c:ResolutionNumber>
                <c:ResolutionDate>2024-01-01</c:ResolutionDate>
                <c:Prefix>SEDS</c:Prefix>
                <c:FromNumber>984000000</c:FromNumber>
                <c:ToNumber>985000000</c:ToNumber>
                <c:ValidDateFrom>2024-01-01</c:ValidDateFrom>
                <c:ValidDateTo>2024-12-31</c:ValidDateTo>
                <c:TechnicalKey i:nil="true"/>
            </c:NumberRangeResponse>

        :return: a dict mapping the odoo field names to their value
        """
        values = {}
        for fname, xpath in [
            ('l10n_co_edi_dian_authorization_number', 'ResolutionNumber'),
            ('l10n_co_edi_dian_authorization_date', 'ValidDateFrom'),
            ('l10n_co_edi_dian_authorization_end_date', 'ValidDateTo'),
            ('l10n_co_edi_min_range_number', 'FromNumber'),
            ('l10n_co_edi_max_range_number', 'ToNumber'),
            ('l10n_co_dian_technical_key', 'TechnicalKey'),
        ]:
            field_value = root.findtext("./{*}" + xpath)
            if field_value:
                values[fname] = field_value
        return values

    def _l10n_co_dian_get_journal_values(self, root):
        prefix_to_values = {}
        for range_node in root.iterfind(".//{*}NumberRangeResponse"):
            journal_prefix = range_node.findtext("./{*}Prefix")
            new_range = self._l10n_co_dian_parse_numbering_range_node(range_node)
            if not prefix_to_values.get(journal_prefix) or int(new_range['l10n_co_edi_min_range_number']) > int(prefix_to_values[journal_prefix]['l10n_co_edi_min_range_number']):
                prefix_to_values[journal_prefix] = new_range
        return prefix_to_values

    def _l10n_co_dian_update_journal(self, journal_values):
        """ Update the journal using the dict 'journal_values' if some values differ from the ones already set.
        :return: True if some fields were updated on the journal, False otherwise
        """
        new_values = {}
        for fname, expected_value in journal_values.items():
            if str(self[fname]) != expected_value:
                new_values[fname] = expected_value

        if new_values:
            chatter_msg = Markup("<ul>")
            for fname, new_val in new_values.items():
                previous_val = self[fname] or ''
                chatter_msg += Markup(
                    "<li>%s: %s%s%s</li>"
                ) % (fname, previous_val, ' -> ' if previous_val else '', new_val)
            chatter_msg += Markup("</ul>")
            self.write(new_values)
            self.message_post(body=_("Updated the following journal values: %s", chatter_msg))

        return bool(new_values)

    def _l10n_co_dian_process_numbering_range_response(self, response):
        if not response['response']:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "error",
                    "message": _("The DIAN server did not respond."),
                    "next": {"type": "ir.actions.act_window_close"},
                }
            }
        root = etree.fromstring(response['response'])
        operation_code = root.findtext(".//{*}OperationCode")
        if operation_code != "100":
            raise UserError(_(
                'DIAN returned error %(code)s: "%(message)s"',
                code=operation_code,
                message=root.findtext(".//{*}OperationDescription"),
            ))

        prefix_to_values = self._l10n_co_dian_get_journal_values(root)
        journal_values = prefix_to_values.get(self.code)
        if not journal_values:
            expected_journal_prefixes = ", ".join(prefix_to_values.keys())
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": _(
                        "No matching numbering range found for journal with short code '%(actual)s'. Found '%(expected)s' instead.",
                        actual=self.code,
                        expected=expected_journal_prefixes,
                    ),
                    "next": {"type": "ir.actions.act_window_close"},
                }
            }
        is_updated = self._l10n_co_dian_update_journal(journal_values)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": _("The journal values were successfully updated.") if is_updated else _("The journal values are already up to date."),
                "next": {"type": "ir.actions.act_window_close"},
            }
        }

    def button_l10n_co_dian_fetch_numbering_range(self):
        self.ensure_one()
        mode = 'bill' if self.type == 'purchase' else 'invoice'
        software_code = self.company_id.l10n_co_dian_operation_mode_ids.filtered(
            lambda operation_mode: operation_mode.dian_software_operation_mode == mode
        )
        vat = self.company_id.partner_id._get_vat_without_verification_code()
        response = xml_utils._build_and_send_request(
            self,
            payload={
                'account_code': vat,
                'account_code_t': vat,
                'software_code': software_code.dian_software_id,
                'soap_body_template': "l10n_co_dian.get_numbering_range",
            },
            service="GetNumberingRange",
            company=self.company_id,
        )
        return self._l10n_co_dian_process_numbering_range_response(response)
