from odoo import Command, _, api, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.account.tools.import_file_type import CUSTOMIZATION_ID, findtext_equals

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_edi_builders(self):
        return super()._get_edi_builders() + [self.env["sale.edi.xml.ubl_bis3"]]

    def _import_file_type_rules(self):
        return [
            (
                "sale.edi.xml.ubl_bis3",
                findtext_equals(
                    CUSTOMIZATION_ID, "urn:fdc:peppol.eu:poacc:trns:order:3"
                ),
            ),
            *super()._import_file_type_rules(),
        ]

    def _get_edi_decoder(self, file_data, new=False):
        if file_data["import_file_type"] == "sale.edi.xml.ubl_bis3":
            _debug.logic("edi_decoder", orders=self, format="ubl_bis3")
            return {
                "priority": 20,
                "decoder": self.env["sale.edi.xml.ubl_bis3"]._import_order_ubl,
            }
        return super()._get_edi_decoder(file_data, new)

    def _create_activity_set_details(self, body):
        activity_message = _("Some information could not be imported:")
        activity_message += body
        _debug.lifecycle("edi_import_incomplete", orders=self)
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=self.env.user.id,
            note=activity_message,
        )

    @api.model
    def _prepare_edi_line_vals(self, lines_vals):

        return [
            {
                "sequence": 0,
                "name": name,
                "product_qty": quantity,
                "price_unit": price_unit,
                "tax_ids": [Command.set(tax_ids)],
            }
            for name, quantity, price_unit, tax_ids in lines_vals
        ]
