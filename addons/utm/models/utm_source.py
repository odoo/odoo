from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UtmSource(models.Model):
    _name = "utm.source"
    _description = "UTM Source"

    name = fields.Char(
        string="Source Name",
        required=True,
    )

    _unique_name = models.Constraint(
        "UNIQUE(name)",
        "The name must be unique",
    )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_referral(self):
        utm_source_referral = self.env.ref(
            "utm.utm_source_referral", raise_if_not_found=False
        )
        for record in self:
            if record == utm_source_referral:
                raise ValidationError(
                    _("You cannot delete the 'Referral' UTM source record.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        new_names = self.env["mixin.utm"]._get_unique_names(
            self._name, [vals.get("name") for vals in vals_list]
        )
        for vals, new_name in zip(vals_list, new_names, strict=True):
            vals["name"] = new_name
        return super().create(vals_list)

    def _generate_name(self, record, content):
        """Generate the UTM source name based on the content of the source."""
        if not content:
            return False

        content = content.replace("\n", " ")
        if len(content) >= 24:
            content = f"{content[:20]}..."

        create_date = record.create_date or fields.Datetime.today()
        model_description = self.env["ir.model"]._get(record._name).name
        return _(
            "%(content)s (%(model_description)s created on %(create_date)s)",
            content=content,
            model_description=model_description,
            create_date=fields.Date.to_string(create_date),
        )
