from odoo import api, fields, models

from .iot_box import REGISTRY_DEFAULTS


class IotDevice(models.Model):
    _name = "iot.device"
    _description = "IOT Device"
    _inherits = {"device.device": "device_id"}

    device_id = fields.Many2one(
        comodel_name="device.device",
        required=True,
        ondelete="cascade",
        help="The registry entry for this peripheral, a part of its box's.",
    )
    iot_id = fields.Many2one(
        comodel_name="iot.box",
        string="IoT Box",
        index=True,
        required=True,
        ondelete="cascade",
    )
    type = fields.Selection(
        selection=[
            ("printer", "Printer"),
            ("camera", "Camera"),
            ("keyboard", "Keyboard"),
            ("scanner", "Barcode Scanner"),
            ("device", "Device"),
            ("payment", "Payment Terminal"),
            ("scale", "Scale"),
            ("display", "Display"),
            ("fiscal_data_module", "Fiscal Data Module"),
            ("unsupported", "Unsupported"),
        ],
        default="device",
        readonly=True,
        help="Type of device.",
    )
    manufacturer = fields.Char(readonly=True)
    connection = fields.Selection(
        selection=[
            ("network", "Network"),
            ("direct", "USB"),
            ("bluetooth", "Bluetooth"),
            ("serial", "Serial"),
            ("hdmi", "HDMI"),
        ],
        readonly=True,
        help="Type of connection.",
    )
    report_ids = fields.Many2many(
        comodel_name="ir.actions.report",
        string="Reports",
    )
    iot_ip = fields.Char(related="iot_id.ip")
    keyboard_layout = fields.Many2one(comodel_name="iot.keyboard.layout")
    display_url = fields.Char(
        string="Display URL",
        help="URL of the page that will be displayed by the device, "
        "leave empty for the default page of whichever app claims it.",
    )
    manual_measurement = fields.Boolean(
        compute="_compute_manual_measurement",
        help="Manually read the measurement from the device",
    )
    is_scanner = fields.Boolean(
        compute="_compute_is_scanner",
        inverse="_inverse_is_scanner",
        help="Manually switch the device type between keyboard and scanner",
    )
    subtype = fields.Selection(
        selection=[
            ("receipt_printer", "Receipt Printer"),
            ("label_printer", "Label Printer"),
            ("office_printer", "Office Printer"),
            ("", ""),
        ],
        default="",
        help="Subtype of device.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        boxes = self.env["iot.box"].browse(
            {vals["iot_id"] for vals in vals_list if vals.get("iot_id")}
        )
        by_box = {box.id: box for box in boxes}
        kinds = self._device_kinds()
        for vals in vals_list:
            for field_name, default in REGISTRY_DEFAULTS.items():
                vals.setdefault(field_name, default)
            box = by_box.get(vals.get("iot_id"))
            if box:
                vals.setdefault("parent_id", box.device_id.id)
                vals.setdefault("company_id", box.company_id.id)
            kind = kinds.get(vals.get("type") or "device")
            if kind and not vals.get("device_category_id"):
                vals["device_category_id"] = kind
        return super().create(vals_list)

    def write(self, vals):
        if "iot_id" in vals:
            box = self.env["iot.box"].browse(vals["iot_id"])
            vals.setdefault("parent_id", box.device_id.id)
        if "type" in vals:
            kind = self._device_kinds().get(vals["type"] or "device")
            if kind:
                vals.setdefault("device_category_id", kind)
        return super().write(vals)

    def unlink(self):
        registry_rows = self.device_id
        result = super().unlink()
        registry_rows.unlink()
        return result

    @api.model
    def _device_kinds(self) -> dict[str, int]:
        """The registry kind that answers for each device type.

        Read by xml id rather than stored on the selection, so a module that
        adds a type ships its kind beside it and nothing here has to know.
        """
        kinds = {}
        for value, _label in self._fields["type"].selection:
            record = self.env.ref(f"iot.kind_iot_{value}", raise_if_not_found=False)
            if record:
                kinds[value] = record.id
        return kinds

    @api.depends("name", "iot_id", "connection")
    @api.depends_context("formatted_display_name")
    def _compute_display_name(self):
        connection_display_values = dict(self._fields["connection"].selection)
        for device in self:
            if device.env.context.get("formatted_display_name"):
                connection = (
                    connection_display_values.get(device.connection, device.connection)
                    if device.connection
                    else ""
                )
                device.display_name = (
                    f"{device.name} \t --{connection}-- \t --{device.iot_id.name}--"
                )
            else:
                device.display_name = f"{device.name}"

    @api.depends("type")
    def _compute_is_scanner(self):
        for device in self:
            device.is_scanner = device.type == "scanner"

    def _inverse_is_scanner(self):
        for device in self:
            device.type = "scanner" if device.is_scanner else "keyboard"

    @api.model
    def _get_manual_measurement_manufacturers(self):
        """Manufacturers whose devices only report a value when asked.

        A driver module adds its own manufacturer here rather than editing the
        compute, so the base app names no vendor.
        """
        return set()

    @api.depends("manufacturer")
    def _compute_manual_measurement(self):
        manufacturers = self._get_manual_measurement_manufacturers()
        for device in self:
            device.manual_measurement = device.manufacturer in manufacturers


class IotKeyboardLayout(models.Model):
    _name = "iot.keyboard.layout"
    _description = "Keyboard Layout"

    name = fields.Char()
    layout = fields.Char()
    variant = fields.Char()
