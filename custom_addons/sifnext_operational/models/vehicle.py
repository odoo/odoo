from odoo import fields, models


class SifnextOperationalVehicle(models.Model):
    _name = "sifnext.operational.vehicle"
    _description = "SIFNEXT Operational Vehicle"

    name = fields.Char(
        string="Nama Kendaraan",
        required=True,
    )

    license_plate = fields.Char(
        string="Nomor Polisi",
        required=True,
    )

    vehicle_type = fields.Selection(
        [
            ("car", "Mobil"),
            ("bus", "Bus"),
            ("motorcycle", "Motor"),
            ("other", "Lainnya"),
        ],
        string="Jenis Kendaraan",
    )

    brand = fields.Char(
        string="Merk",
    )

    capacity = fields.Integer(
        string="Kapasitas",
    )

    description = fields.Text(
        string="Keterangan",
    )

    active = fields.Boolean(
        string="Aktif",
        default=True,
    )