from odoo import api, fields, models


class GatewayMlPolicy(models.Model):
    _name = "gateway.ml.policy"
    _description = "Machine-Learning Data Policy"
    _order = "company_id, purpose_id"
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        required=True,
    )
    purpose_id = fields.Many2one(
        comodel_name="gateway.ml.purpose",
        index=True,
        ondelete="cascade",
        required=True,
    )
    provider_ids = fields.Many2many(
        comodel_name="gateway.ml.provider",
        string="Allowed vendors",
        help="The vendors this company lets data of this purpose reach. Empty: none.",
    )
    approved_by_id = fields.Many2one(
        comodel_name="res.users",
        readonly=True,
    )
    approved_at = fields.Datetime(readonly=True)
    note = fields.Text()

    _company_purpose_uniq = models.Constraint(
        "unique(company_id, purpose_id)",
        "A company has one policy per purpose.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        return super().create([{**vals, **self._approval_vals()} for vals in vals_list])

    def write(self, vals):
        if "provider_ids" in vals:
            vals = {**vals, **self._approval_vals()}
        return super().write(vals)

    def _approval_vals(self) -> dict:
        return {"approved_by_id": self.env.uid, "approved_at": fields.Datetime.now()}

    @api.model
    def _allowed_providers(self, company_id: int, key: str, providers):
        Purpose = self.env["gateway.ml.purpose"]
        lineage = Purpose._lineage(key)
        policies = self.sudo().search(
            [("company_id", "=", company_id), ("purpose_id.key", "in", lineage)]
        )
        by_key = {policy.purpose_id.key: policy for policy in policies}
        governing = next((by_key[k] for k in lineage if k in by_key), None)
        if governing is not None:
            return providers & governing.provider_ids
        if Purpose._is_sensitive(key):
            return providers.browse()
        return providers
