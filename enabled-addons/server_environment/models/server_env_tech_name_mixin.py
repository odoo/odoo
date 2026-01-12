# Copyright 2020 Camptocamp (http://www.camptocamp.com)
# @author Simone Orsi <simahawk@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

from odoo import api, fields, models


class ServerEnvTechNameMixin(models.AbstractModel):
    """Provides a tech_name field to be used in server env vars as unique key.

    The `name` field can be error prone because users can easily change it
    to something more meaningful for them or set weird chars into it
    that make difficult to reference the record in env var config.
    This mixin helps solve the problem by providing a tech name field
    and a cleanup machinery as well as a unique constrain.

    To use this mixin add it to the _inherit attr of your model like:
    (instead of `server.env.mixin`)

        _inherit = [
            "my.model",
            "server.env.techname.mixin",
        ]

    """

    _name = "server.env.techname.mixin"
    _inherit = "server.env.mixin"
    _description = "Server environment technical name"
    _sql_constraints = [
        (
            "tech_name_uniq",
            "unique(tech_name)",
            "`tech_name` must be unique!",
        )
    ]
    # TODO: could leverage the new option for computable / writable fields
    # and get rid of some onchange / read / write code.
    tech_name = fields.Char(
        help="Unique name for technical purposes. Eg: server env keys.",
        copy=False,
    )

    _server_env_section_name_field = "tech_name"

    @api.onchange("name")
    def _onchange_name_for_tech(self):
        # Keep this specific name for the method to avoid possible overrides
        # of existing `_onchange_name` methods
        if self.name and not self.tech_name:
            self.tech_name = self.name

    @api.onchange("tech_name")
    def _onchange_tech_name(self):
        if self.tech_name:
            # make sure is normalized
            self.tech_name = self._normalize_tech_name(self.tech_name)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._handle_tech_name(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._handle_tech_name(vals)
        return super().write(vals)

    def _handle_tech_name(self, vals):
        # make sure technical names are always there
        if not vals.get("tech_name") and vals.get("name"):
            vals["tech_name"] = self._normalize_tech_name(vals["name"])

    def _normalize_tech_name(self, name):
        return self.env["ir.http"]._slugify(name).replace("-", "_")
