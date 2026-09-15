from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TeamAlias(models.Model):
    _name = "team.alias"
    _inherits = {"mail.alias": "alias_id"}
    _description = "Team Email Alias"
    _rec_name = "alias_name"

    team_id = fields.Many2one(
        comodel_name="team.team",
        index=True,
        required=True,
        ondelete="cascade",
    )
    usage = fields.Char(required=True)
    alias_id = fields.Many2one(
        comodel_name="mail.alias",
        required=True,
        ondelete="cascade",
    )

    _team_id_usage_uniq = models.Constraint(
        "UNIQUE(team_id, usage)",
        "A team has one email alias per usage.",
    )

    @api.constrains("usage")
    def _constrains_usage(self):
        self._check_usage_receives_mail(self.mapped("usage"))

    @api.model
    def _check_usage_receives_mail(self, keys):
        usages = self.env["team.team"]._get_usages()
        for key in keys:
            if key not in usages or not usages[key].alias_model:
                raise ValidationError(
                    self.env._("Usage %(usage)s does not receive email.", usage=key)
                )

    @api.model_create_multi
    def create(self, vals_list):
        self._check_usage_receives_mail([vals.get("usage") for vals in vals_list])
        for vals in vals_list:
            if not vals.get("alias_id"):
                team = self.env["team.team"].browse(vals["team_id"])
                alias_vals = {
                    fname: vals.pop(fname)
                    for fname in list(vals)
                    if fname not in ("team_id", "usage", "alias_id")
                    and fname in self.env["mail.alias"]._fields
                }
                vals["alias_id"] = (
                    self.env["mail.alias"]
                    .sudo()
                    .create(
                        {
                            **team._prepare_usage_alias_vals(vals["usage"]),
                            **alias_vals,
                        }
                    )
                    .id
                )
        return super().create(vals_list)

    def write(self, vals):
        # the mail.alias behind is written as superuser once the row itself may
        # be written, as mixin.mail.alias does for the records that own one
        alias_fields = self.env["mail.alias"]._fields
        alias_vals = {
            fname: vals.pop(fname)
            for fname in list(vals)
            if fname not in ("team_id", "usage", "alias_id") and fname in alias_fields
        }
        # an empty form sends False for the alias fields it shows, and mail.alias
        # requires some of them
        alias_vals = {
            fname: value
            for fname, value in alias_vals.items()
            if value or not alias_fields[fname].required
        }
        res = super().write(vals) if vals else True
        if alias_vals:
            self.check_access("write")
            self.alias_id.sudo().write(alias_vals)
        if "team_id" in vals or "usage" in vals:
            self._refresh_alias_values()
        return res

    def unlink(self):
        aliases = self.alias_id
        res = super().unlink()
        aliases.sudo().unlink()
        return res

    def _refresh_alias_values(self):
        for alias in self:
            values = alias.team_id._prepare_usage_alias_vals(alias.usage)
            if not alias.team_id.company_id.alias_domain_id and alias.alias_domain_id:
                # a team without a company keeps the domain someone chose for it
                values["alias_domain_id"] = alias.alias_domain_id.id
            values["alias_defaults"] = str(
                {
                    **alias.alias_id._prepare_alias_defaults(),
                    **alias.team_id._prepare_usage_alias_defaults(alias.usage),
                }
            )
            alias.alias_id.sudo().write(values)
