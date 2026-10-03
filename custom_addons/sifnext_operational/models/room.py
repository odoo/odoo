from odoo import fields, models


class SifnextOperationalRoom(models.Model):
    _name = "sifnext.operational.room"
    _description = "SIFNEXT Operational Room"
    _order = "name"

    name = fields.Char(
        string="Nama Ruangan",
        required=True,
    )

    location = fields.Char(
        string="Lokasi",
    )

    capacity = fields.Integer(
        string="Kapasitas",
    )

    facilities = fields.Text(
        string="Fasilitas",
    )

    active = fields.Boolean(
        string="Aktif",
        default=True,
    )