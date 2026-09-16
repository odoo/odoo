import copy
from typing import Any

from lxml import etree

from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

ADDRESS_FIELDS = ("street", "street2", "zip", "city", "state_id", "country_id")


class MixinFormatAddress(models.AbstractModel):
    _name = "mixin.format.address"
    _description = "Address Format"

    def _extract_fields_from_address(self, address_line: str) -> list[str]:
        address_fields = [
            "%(" + field + ")s"
            for field in ADDRESS_FIELDS + ("state_code", "state_name")
        ]
        return sorted(
            [field[2:-2] for field in address_fields if field in address_line],
            key=lambda field: address_line.index("%(" + field + ")s"),
        )

    def _view_get_address(self, arch: etree._Element) -> etree._Element:
        address_view_id = self.env.company.country_id.address_view_id.sudo()
        address_format = self.env.company.country_id.address_format
        _debug.pipeline(
            "address_arch",
            model=self._name,
            country=self.env.company.country_id.id,
            view=address_view_id.id,
            has_format=bool(address_format),
            disabled=bool(self.env.context.get("no_address_format")),
        )
        if (
            address_view_id
            and not self.env.context.get("no_address_format")
            and (not address_view_id.model or address_view_id.model == self._name)
        ):
            address_nodes = arch.xpath("//div[hasclass('o_address_format')]")
            _debug.logic(
                "address_view",
                model=self._name,
                view=address_view_id.id,
                nodes=len(address_nodes),
            )
            if address_nodes:
                Partner = self.env["res.partner"].with_context(no_address_format=True)
                sub_arch, _sub_view = Partner._get_view(address_view_id.id, "form")
                if self._name != "res.partner":
                    try:
                        self.env["ir.ui.view"].postprocess_and_fields(
                            sub_arch, model=self._name
                        )
                    except ValueError:
                        _debug.logic("address_view_rejected", model=self._name)
                        return arch
                for address_node in address_nodes:
                    node_arch = copy.deepcopy(sub_arch)
                    new_address_nodes = node_arch.xpath(
                        './/div[hasclass("o_address_format")]'
                    )
                    replacement = (
                        new_address_nodes[0] if new_address_nodes else node_arch
                    )
                    address_node.getparent().replace(address_node, replacement)
        elif address_format and not self.env.context.get("no_address_format"):
            city_line = [
                self._extract_fields_from_address(line)
                for line in address_format.split("\n")
                if "city" in line
            ]
            if _debug.logic.enabled:
                _debug.logic(
                    "address_format_city_line",
                    model=self._name,
                    found=bool(city_line),
                    fields=len(city_line[0]) if city_line else 0,
                )
            if city_line:
                field_order = city_line[0]
                for address_node in arch.xpath("//div[hasclass('o_address_format')]"):
                    first_field = (
                        field_order[0]
                        if field_order[0] not in ("state_code", "state_name")
                        else "state_id"
                    )
                    concerned_fields = ["zip", "city", "state_id"]
                    concerned_fields = [f for f in concerned_fields if f != first_field]
                    current_field = address_node.find(
                        f".//field[@name='{first_field}']"
                    )
                    for field in field_order[1:]:
                        if field in ("state_code", "state_name"):
                            field = "state_id"
                        previous_field = current_field
                        current_field = address_node.find(f".//field[@name='{field}']")
                        if previous_field is not None and current_field is not None:
                            previous_field.addnext(current_field)
                        if field in concerned_fields:
                            concerned_fields.remove(field)
                    for field in concerned_fields:
                        previous_field = current_field
                        current_field = address_node.find(f".//field[@name='{field}']")
                        if previous_field is not None and current_field is not None:
                            previous_field.addnext(current_field)

        return arch

    @api.model
    def _get_view_cache_key(
        self, view_id: int | None = None, view_type: str = "form", **options
    ) -> tuple:
        key = super()._get_view_cache_key(view_id, view_type, **options)
        country = self.env.company.country_id
        return key + (
            country.address_view_id.id,
            country.address_format,
            self.env.context.get("no_address_format"),
        )

    @api.model
    def _get_view(
        self, view_id: int | None = None, view_type: str = "form", **options
    ) -> tuple[etree._Element, Any]:
        arch, view = super()._get_view(view_id, view_type, **options)
        if view.type == "form":
            with _debug.perf("address_view_get", model=self._name, view=view.id):
                arch = self._view_get_address(arch)
        return arch, view
