# Copyright 2019 Alexandre Díaz <dev@redneboa.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
from colorsys import hls_to_rgb, rgb_to_hls

from odoo import api, fields, models

from ..utils import convert_to_image, image_to_rgb, n_rgb_to_hex

URL_BASE = "/web_company_color/static/src/scss/"
URL_SCSS_GEN_TEMPLATE = URL_BASE + "custom_colors.%d.gen.scss"


class ResCompany(models.Model):
    _inherit = "res.company"

    SCSS_TEMPLATE = """
        .o_main_navbar {
          background: %(color_navbar_bg)s !important;
          background-color: %(color_navbar_bg)s !important;
          color: %(color_navbar_text)s !important;

          > .o_menu_brand {
            color: %(color_navbar_text)s !important;
            &:hover, &:focus, &:active, &:focus:active {
              background-color: %(color_navbar_bg_hover)s !important;
            }
          }

          .show {
            .dropdown-toggle {
              background-color: %(color_navbar_bg_hover)s !important;
            }
          }

          > ul {
            > li {
              > a, > label {
                color: %(color_navbar_text)s !important;

                &:hover, &:focus, &:active, &:focus:active {
                  background-color: %(color_navbar_bg_hover)s !important;
                }
              }
            }
          }
        }
        a[href],
        a[tabindex],
        .btn-link,
        .o_external_button {
          color: %(color_link_text)s !important;
        }
        a:hover,
        .btn-link:hover {
          color: %(color_link_text_hover)s !important;
        }
        .btn-primary:not(.disabled),
        .ui-autocomplete .ui-menu-item > a.ui-state-active {
          color: %(color_button_text)s !important;
          background-color: %(color_button_bg)s !important;
          border-color: %(color_button_bg)s !important;
        }
        .btn-primary:hover:not(.disabled),
        .ui-autocomplete .ui-menu-item > a.ui-state-active:hover {
          color: %(color_button_text)s !important;
          background-color: %(color_button_bg_hover)s !important;
          border-color: %(color_button_bg_hover)s !important;
        }
        .o_searchview .o_searchview_facet .o_searchview_facet_label {
          color: %(color_button_text)s !important;
          background-color: %(color_button_bg)s !important;
        }
        .o_form_view .o_horizontal_separator {
          color: %(color_link_text)s !important;
        }
        .o_form_view .oe_button_box .oe_stat_button .o_button_icon,
        .o_form_view .oe_button_box .oe_stat_button .o_stat_info .o_stat_value,
        .o_form_view .oe_button_box .oe_stat_button > span .o_stat_value {
          color: %(color_link_text)s !important;
        }
        .o_form_view .o_form_statusbar > .o_statusbar_status >
        .o_arrow_button.btn-primary.disabled {
          color: %(color_link_text)s !important;
        }
        .o_required_modifier.o_input, .o_required_modifier .o_input {
          background-color: lighten(%(color_button_bg)s, 10%%) !important;
        }
    """

    company_colors = fields.Serialized()
    color_navbar_bg = fields.Char("Navbar Background Color", sparse="company_colors")
    color_navbar_bg_hover = fields.Char(
        "Navbar Background Color Hover", sparse="company_colors"
    )
    color_navbar_text = fields.Char("Navbar Text Color", sparse="company_colors")
    color_button_text = fields.Char("Button Text Color", sparse="company_colors")
    color_button_bg = fields.Char("Button Background Color", sparse="company_colors")
    color_button_bg_hover = fields.Char(
        "Button Background Color Hover", sparse="company_colors"
    )
    color_link_text = fields.Char("Link Text Color", sparse="company_colors")
    color_link_text_hover = fields.Char(
        "Link Text Color Hover", sparse="company_colors"
    )
    scss_modif_timestamp = fields.Char("SCSS Modif. Timestamp")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.scss_create_or_update_attachment()
        return records

    def unlink(self):
        IrAttachmentObj = self.env["ir.attachment"]
        for record in self:
            IrAttachmentObj.sudo().search(
                [("url", "=", record.scss_get_url()), ("company_id", "=", record.id)]
            ).sudo().unlink()
        return super().unlink()

    def write(self, values):
        if not self.env.context.get("ignore_company_color", False):
            fields_to_check = (
                "color_navbar_bg",
                "color_navbar_bg_hover",
                "color_navbar_text",
                "color_button_bg",
                "color_button_bg_hover",
                "color_button_text",
                "color_link_text",
                "color_link_text_hover",
            )
            result = super().write(values)
            if any([field in values for field in fields_to_check]):
                self.scss_create_or_update_attachment()
        else:
            result = super().write(values)
        return result

    def button_compute_color(self):
        self.ensure_one()
        values = self.default_get(
            ["color_navbar_bg", "color_navbar_bg_hover", "color_navbar_text"]
        )
        if self.logo:
            _r, _g, _b = image_to_rgb(convert_to_image(self.logo))
            # Make color 10% darker
            _h, _l, _s = rgb_to_hls(_r, _g, _b)
            _l = max(0, _l - 0.1)
            _rd, _gd, _bd = hls_to_rgb(_h, _l, _s)
            # Calc. optimal text color (b/w)
            # Grayscale human vision perception (Rec. 709 values)
            _a = 1 - (0.2126 * _r + 0.7152 * _g + 0.0722 * _b)
            values.update(
                {
                    "color_navbar_bg": n_rgb_to_hex(_r, _g, _b),
                    "color_navbar_bg_hover": n_rgb_to_hex(_rd, _gd, _bd),
                    "color_navbar_text": "#000" if _a < 0.5 else "#fff",
                }
            )
        self.write(values)

    def _scss_get_sanitized_values(self):
        self.ensure_one()
        # Clone company_color as dictionary to avoid ORM operations
        # This allow extend company_colors and only sanitize selected fields
        # or add custom values
        values = dict(self.company_colors or {})
        values.update(
            {
                "color_navbar_bg": (values.get("color_navbar_bg") or "$o-brand-odoo"),
                "color_navbar_bg_hover": (values.get("color_navbar_bg_hover")),
                "color_navbar_text": (values.get("color_navbar_text") or "#FFF"),
                "color_button_bg": values.get("color_button_bg") or "$primary",
                "color_button_bg_hover": values.get("color_button_bg_hover")
                or 'darken(theme-color("primary"), 10%)',
                "color_button_text": values.get("color_button_text") or "#FFF",
                "color_link_text": values.get("color_link_text")
                or 'theme-color("primary")',
                "color_link_text_hover": values.get("color_link_text_hover")
                or 'darken(theme-color("primary"), 10%)',
            }
        )
        return values

    def _scss_generate_content(self):
        self.ensure_one()
        # ir.attachment need files with content to work
        if not self.company_colors:
            return "// No Web Company Color SCSS Content\n"
        return self.SCSS_TEMPLATE % self._scss_get_sanitized_values()

    def scss_get_url(self):
        self.ensure_one()
        return URL_SCSS_GEN_TEMPLATE % self.id

    def scss_create_or_update_attachment(self):
        IrAttachmentObj = self.env["ir.attachment"]
        for record in self:
            datas = base64.b64encode(record._scss_generate_content().encode("utf-8"))
            custom_url = record.scss_get_url()
            custom_attachment = IrAttachmentObj.sudo().search(
                [("url", "=", custom_url), ("company_id", "=", record.id)]
            )
            values = {
                "datas": datas,
                "db_datas": datas,
                "url": custom_url,
                "name": custom_url,
                "company_id": record.id,
            }
            if custom_attachment:
                custom_attachment.sudo().write(values)
            else:
                values.update({"type": "binary", "mimetype": "text/scss"})
                IrAttachmentObj.sudo().create(values)
        self.env["ir.qweb"].sudo().clear_caches()
