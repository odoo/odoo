from typing import TYPE_CHECKING, Any

from odoo import api, models

if TYPE_CHECKING:
    from lxml import etree


class FormatVatLabelMixin(models.AbstractModel):
    _name = "format.vat.label.mixin"
    _description = "Country Specific VAT Label"

    @api.model
    def _get_view(
        self, view_id: int | None = None, view_type: str = "form", **options
    ) -> tuple[etree._Element, Any]:
        arch, view = super()._get_view(view_id, view_type, **options)
        if vat_label := self.env.company.country_id.vat_label:
            for node in arch.iterfind(".//field[@name='vat']"):
                node.set("string", vat_label)
            # In some module vat field is replaced and so above string change is not working
            for node in arch.iterfind(".//label[@for='vat']"):
                node.set("string", vat_label)
        return arch, view
