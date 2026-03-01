from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.l10n_pk_edi.data.l10n_pk_edi_data import SALE_TYPE


class L10nPkEdiSro(models.Model):
    _name = "l10n_pk_edi.sro"
    _description = "Pakistan Statutory Regulatory Order"

    name = fields.Char(string="Statutory Regulatory Order Schedule")
    sro_item_ids = fields.One2many("l10n_pk_edi.sro.item", 'sro_id', string="Statutory Regulatory Order Items")
    l10n_pk_edi_sale_type = fields.Selection(selection=SALE_TYPE, string="Sale Type", required=True)

    @api.constrains('name', 'l10n_pk_edi_sale_type')
    def _constraint_sro_name(self):
        # One aggregate query for the whole recordset: the database reports every (name, sale type)
        # pair occurring more than once, so nothing is fetched or compared in Python.
        duplicates = self._read_group(
            domain=[
                ('name', 'in', self.mapped('name')),
                ('l10n_pk_edi_sale_type', 'in', self.mapped('l10n_pk_edi_sale_type')),
            ],
            groupby=['name', 'l10n_pk_edi_sale_type'],
            having=[('__count', '>', 1)],
        )
        if duplicates:
            raise ValidationError(self.env._(
                "A Statutory Regulatory Order with this name already exists for its Sale Type: %(names)s",
                names=", ".join(name or self.env._("Unnamed") for name, __ in duplicates),
            ))
