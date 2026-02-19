import base64
from io import BytesIO
from PIL import Image, ImageOps

from odoo import api, fields, models, _


epos_template = """
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <epos-print xmlns="http://www.epson-pos.com/schemas/2011/03/epos-print">
            <image width="576" height="%s" align="center">%s</image>
            <cut type="feed" />
        </epos-print>
    </s:Body>
</s:Envelope>
"""


def thermal_printer_format(data) -> str:
    """Render the report and convert it to a black and white image
    with a width of 576px to fit the ePOS printer paper width"""
    img = Image.open(BytesIO(data)).convert("L")  # convert to grayscale

    if img.width > img.height:
        img = img.rotate(90, expand=True)  # ensure portrait mode

    target_width = 576
    ratio = target_width / img.width
    target_height = int(img.height * ratio)  # Preserve aspect ratio
    img = ImageOps.invert(img).resize((target_width, target_height), Image.ANTIALIAS).convert("1", dither=Image.FLOYDSTEINBERG)
    base64_image = base64.b64encode(img.tobytes()).decode()

    return epos_template % (target_height, base64_image)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    printer_ids = fields.Many2many("printer.printer", string="Printers")

    @api.model
    def get_print_jobs(self, report_name, docids, data) -> list:
        """Method to render reports for printers.

        This method is meant to be overridden by modules adding support
        for specific printer types (e.g. ePOS, IoT).

        By default, we render ZPL reports, PDF ones will be handled using
        Odoo's default behavior.
        """
        report = self._get_report(report_name)
        if report.report_type == "qweb-text" and ".zpl" in report.name.lower():
            return [{
                "type": "zpl",
                "report": base64.b64encode(self._render(report_name, docids, data=data)[0]),
            }]
        return []

    def _read_format(self, *args, **kwargs):
        """Override to add printer IPs and jobs to the context,
        in order to avoid a second RPC call to get attachments"""
        res = super()._read_format(*args, **kwargs)
        docids = self.env.context.get("active_ids") or []
        if not kwargs.get("load") or not len(self.printer_ids.exists()) or not docids:
            return res

        printer_ids = self.printer_ids.mapped(lambda p: {
            "id": p.id,
            "ip_address": p.ip_address,
        })
        jobs = self.with_context(bin_size=False).get_print_jobs(self.report_name, docids, {})
        for record in res:
            record.setdefault("context", {})
            record["context"].update({
                "report_id": self.id,
                "jobs": jobs,
                "printer_ids": printer_ids,
            })
        return res

    def report_action(self, docids=None, data=None, config=True):
        res = super().report_action(docids, data, config)
        if not len(self.printer_ids.exists()):
            return res

        res["context"] = {
            **dict(res.get("context", {})),
            "report_id": self.id,
            "jobs": self.get_print_jobs(self.report_name, docids, data),
            "printer_ids": self.printer_ids.mapped(lambda p: {
                "id": p.id,
                "ip_address": p.ip_address,
            }),
        }
        return res

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {
            "printer_ids",
        }

    def get_select_printer_wizard(self, context=None):
        """
        :param dict context: printers already selected by the user,
        saved in local storage
        """
        self.ensure_one()
        context = context or {}
        selected_printers = {p["id"] for p in context.get("selectedPrinters", [])}
        # Filter out printers that are deleted/no longer linked to the report
        printer_ids = self.printer_ids.filtered(lambda p: p.id in selected_printers)
        wizard = self.env["select.printers.wizard"].create([{
            "printer_ids": printer_ids.ids,
        }])
        return {
            "name": _("Select Printers for %s", self.name),
            "res_id": wizard.id,
            "type": "ir.actions.act_window",
            "res_model": "select.printers.wizard",
            "target": "new",
            "views": [[False, "form"]],
            "context": {
                "report_id": self.id,
                # hack to get `id` + `ip_address` without doing another RPC call in the wizard FormController
                "printer_ids": self.printer_ids.mapped(lambda p: {
                    "id": p.id,
                    "ip_address": p.ip_address,
                }),
                "available_printer_ids": self.printer_ids.ids,
            },
        }
