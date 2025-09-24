from odoo import models, fields

class VersioningMixin(models.AbstractModel):
    _name = "mail.versioning.mixin"
    _description = "Mixin to add versioning to a model"

    version = fields.Integer(string="Version", default=1)

    def create(self, vals_list):
        if not isinstance(vals_list, list):
            if "version" in vals_list:
                raise ValueError("Direct modification of 'version' field is not allowed.")
            vals_list["version"] = 1
        else:
            for vals in vals_list:
                if "version" in vals:
                    raise ValueError("Direct modification of 'version' field is not allowed.")
                vals["version"] = 1
        return super().create(vals_list)

    def write(self, vals):
        self.ensure_one()
        if "version" in vals:
            raise ValueError("Direct modification of 'version' field is not allowed.")
        vals["version"] = self.version + 1
        res = super().write(vals)
        return res
