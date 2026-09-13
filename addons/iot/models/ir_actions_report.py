import base64

from lxml.etree import ParserError

from odoo import _, fields, models
from odoo.exceptions import UserError


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    device_ids = fields.Many2many(
        comodel_name="iot.device",
        string="IoT Devices",
        domain="[('type', '=', 'printer')]",
        help="When setting a device here, the report will be printed through this device on the IoT Box",
    )

    def render_document(self, device_id_list, res_ids, data=None):
        """Render a document to be printed by the IoT Box through client

        :param device_id_list: The list of device ids to print the document
        :param res_ids: The list of record ids to print
        :param data: The data to pass to the report
        :return: The list of documents to print with information about the device
        """
        device_ids = self.env["iot.device"].browse(device_id_list)
        if len(device_id_list) != len(device_ids.exists()):
            raise UserError(
                _(
                    "One of the printer used to print the document has been removed.\n"
                    'To reset printers, go to the IoT App, Configuration tab, "Reset Linked Printers" and retry the operation.'
                )
            )

        datas = self._render(self.report_name, res_ids, data=data)
        data_bytes = datas[0]
        data_base64 = base64.b64encode(data_bytes)
        return [
            {
                "iotBoxId": device.iot_id.id,
                "deviceId": device.id,
                "deviceIdentifier": device.identifier,
                "deviceName": device.display_name,
                "document": data_base64,
            }
            for device in device_ids
        ]  # As it is called via JS, we format keys to camelCase

    def report_action(self, docids, data=None, config=True):
        result = super().report_action(docids, data, config)
        if result.get("type") != "ir.actions.report":
            return result
        device = self.device_ids and self.device_ids[0]
        if data and data.get("device_id"):
            device = self.env["iot.device"].browse(data["device_id"])

        result["id"] = self.id
        result["device_ids"] = device.mapped("identifier")
        return result

    def _get_fields_readable(self):
        return super()._get_fields_readable() | {
            "device_ids",
        }

    def get_action_wizard(self, selected_device_ids=None):
        self.check_singleton()
        if selected_device_ids:
            selected_device_ids = [
                dev for dev in selected_device_ids if dev in self.device_ids.ids
            ]  # Filter out devices that are deleted/no longer linked to the report
        wizard = self.env["select.printers.wizard"].create(
            [{"display_device_ids": self.device_ids, "device_ids": selected_device_ids}]
        )
        return {
            "name": _("Select Printers for %s", self.name),
            "res_id": wizard.id,
            "type": "ir.actions.act_window",
            "res_model": "select.printers.wizard",
            "target": "new",
            "views": [[False, "form"]],
            "context": {
                "report_id": self.id,
            },
        }

    def _render_qweb_pdf(self, report_ref, *args, **kwargs):
        """Override to ensure the user is informed when trying to print an empty report
        without an IoT printer.

        This can happen when trying to print delivery labels, that have empty reports used for assigning
        IoT printers.
        """
        try:
            return super()._render_qweb_pdf(report_ref, *args, **kwargs)
        except ParserError:
            raise UserError(
                _(
                    "The report you are trying to print requires an IoT Box to be printed.\n"
                    "Make sure you linked the report '%s' to the corresponding IoT printer device.",
                    report_ref,
                )
            )
