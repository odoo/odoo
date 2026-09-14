from odoo import api, models


class ResConfigSettings(models.TransientModel):
    """Settings fields declared with ``secret_parameter="<key>"``.

    They read and write an encrypted setting credential instead of an
    ``ir.config_parameter`` row, which every backup carries in clear.
    """

    _inherit = "res.config.settings"

    def _is_valid_field_parameter(self, field, name):
        return name == "secret_parameter" or super()._is_valid_field_parameter(
            field, name
        )

    def _secret_parameter_fields(self):
        return {
            name: field.secret_parameter
            for name, field in self._fields.items()
            if getattr(field, "secret_parameter", None)
        }

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        Credential = self.env["credential.credential"]
        for name, key in self._secret_parameter_fields().items():
            if name in fields:
                res[name] = Credential._get_system_secret(key)
        return res

    def set_values(self):
        super().set_values()
        Credential = self.env["credential.credential"]
        for name, key in self._secret_parameter_fields().items():
            value = (self[name] or "").strip() or False
            if value != Credential._get_system_secret(key):
                Credential._set_system_secret(key, value)
