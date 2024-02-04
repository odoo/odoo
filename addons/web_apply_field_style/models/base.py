# © 2023 David BEAL @ Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, exceptions, models

logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == "form":
            self._update_css_class(arch)
        return arch, view

    def _update_css_class(self, arch):
        css = self._get_field_styles()
        if css:
            self._check_css_dict(css)
            for style in css.get(self._name):
                for field_name in css[self._name][style]:
                    for field in arch.xpath(f"//field[@name='{field_name}']"):
                        field.attrib[
                            "class"
                        ] = f"{style} {field.attrib.get('class') or ''}".strip()

    def _get_field_styles(self):
        """Inherit me with:

        res = super()._get_field_styles()
        res.append({'my_model': {"css_class": ['field1', 'field2'], "bg-info": [...] }})
        return res
        """
        return {}

    def _check_css_dict(self, css):
        rtfm = "\n\nPlease have a look to the readme.\n\nThe rtfm team."
        if not isinstance(css, dict):
            raise exceptions.ValidationError(
                f"_get_field_styles() should return a dict{rtfm}"
            )
        model = self._name
        if model in css:
            if not isinstance(css[model], dict):
                raise exceptions.ValidationError(f"{css[model]} should be a dict{rtfm}")
            for vals in css[model].values():
                if not isinstance(vals, list):
                    raise exceptions.ValidationError(
                        f"{vals} should be a list of fields !{rtfm}"
                    )
