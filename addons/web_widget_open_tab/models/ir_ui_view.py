# Copyright 2023 Quartile Limited
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import api, models


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        model = self.env["ir.model"]._get(self._name)
        if view_type == "tree" and model.add_open_tab_field:
            id_elem = """<field name="id" widget="open_tab" nolabel="1"/>"""
            id_elem = etree.fromstring(id_elem)
            tree = arch.xpath("//tree")[0]
            name_field = tree.xpath('./field[@name="name"]')
            if name_field:
                tree.insert(name_field[0].getparent().index(name_field[0]) + 1, id_elem)
            else:
                tree.insert(0, id_elem)
        return arch, view
