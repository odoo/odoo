from typing import TYPE_CHECKING, Any

from odoo import api, models

if TYPE_CHECKING:
    from lxml import etree

ADDRESS_FIELDS = ("street", "street2", "zip", "city", "state_id", "country_id")


class FormatAddressMixin(models.AbstractModel):
    _name = "format.address.mixin"
    _description = "Address Format"

    def _extract_fields_from_address(self, address_line: str) -> list[str]:
        """
        Extract keys from the address line.
        For example, if the address line is "zip: %(zip)s, city: %(city)s.",
        this method will return ['zip', 'city'].
        """
        address_fields = [
            "%(" + field + ")s"
            for field in ADDRESS_FIELDS + ("state_code", "state_name")
        ]
        return sorted(
            [field[2:-2] for field in address_fields if field in address_line],
            key=address_line.index,
        )

    def _view_get_address(self, arch: etree._Element) -> etree._Element:
        # consider the country of the user, not the country of the partner we want to display
        address_view_id = self.env.company.country_id.address_view_id.sudo()
        address_format = self.env.company.country_id.address_format
        if (
            address_view_id
            and not self.env.context.get("no_address_format")
            and (not address_view_id.model or address_view_id.model == self._name)
        ):
            # render the partner address accordingly to address_view_id
            for address_node in arch.xpath("//div[hasclass('o_address_format')]"):
                Partner = self.env["res.partner"].with_context(no_address_format=True)
                sub_arch, _sub_view = Partner._get_view(address_view_id.id, "form")
                # if the model is different than res.partner, there are chances that the view won't work
                # (e.g fields not present on the model). In that case we just return arch
                if self._name != "res.partner":
                    try:
                        self.env["ir.ui.view"].postprocess_and_fields(
                            sub_arch, model=self._name
                        )
                    except ValueError:
                        return arch
                new_address_node = sub_arch.find('.//div[@class="o_address_format"]')
                if new_address_node is not None:
                    sub_arch = new_address_node
                address_node.getparent().replace(address_node, sub_arch)
        elif address_format and not self.env.context.get("no_address_format"):
            # For the zip, city and state fields we need to move them around in order to follow the country address format.
            # The purpose of this is to help the user by following a format he is used to.
            city_line = [
                self._extract_fields_from_address(line)
                for line in address_format.split("\n")
                if "city" in line
            ]
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
                    # First loop into the fields displayed in the address_format, and order them.
                    for field in field_order[1:]:
                        if field in ("state_code", "state_name"):
                            field = "state_id"
                        previous_field = current_field
                        current_field = address_node.find(f".//field[@name='{field}']")
                        if previous_field is not None and current_field is not None:
                            previous_field.addnext(current_field)
                        if field in concerned_fields:
                            concerned_fields.remove(field)
                    # Add the remaining fields in 'concerned_fields' at the end, after the others
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
        """The override of _get_view, using _view_get_address,
        changing the architecture according to the address view of the company,
        makes the view cache dependent on the company.
        Different companies could use each a different address view"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (
            self.env.company,
            self.env.context.get("no_address_format"),
        )

    @api.model
    def _get_view(
        self, view_id: int | None = None, view_type: str = "form", **options
    ) -> tuple[etree._Element, Any]:
        arch, view = super()._get_view(view_id, view_type, **options)
        if view.type == "form":
            arch = self._view_get_address(arch)
        return arch, view
