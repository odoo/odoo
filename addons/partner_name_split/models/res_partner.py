from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    firstname = fields.Char(string="Nombre")
    lastname = fields.Char(string="Apellidos")

    @staticmethod
    def _compose_name(firstname, lastname):
        firstname = (firstname or "").strip()
        lastname = (lastname or "").strip()
        return " ".join(part for part in [firstname, lastname] if part)

    @staticmethod
    def _split_name(name):
        name = (name or "").strip()
        if not name:
            return "", ""
        parts = name.split()
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])

    @api.onchange("firstname", "lastname", "company_type")
    def _onchange_name_parts(self):
        for partner in self:
            if partner.company_type != "person":
                continue
            partner.name = self._compose_name(partner.firstname, partner.lastname)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sync_name_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        self._sync_name_vals(vals)
        return super().write(vals)

    def _sync_name_vals(self, vals):
        company_type = vals.get("company_type")
        if company_type == "company":
            return

        has_first = "firstname" in vals
        has_last = "lastname" in vals
        has_name = "name" in vals

        if has_first or has_last:
            vals["name"] = self._compose_name(vals.get("firstname"), vals.get("lastname"))
            return

        if has_name:
            first, last = self._split_name(vals.get("name"))
            vals.setdefault("firstname", first)
            vals.setdefault("lastname", last)
