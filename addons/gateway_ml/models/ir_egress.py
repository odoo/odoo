from odoo import api, models


class IrEgress(models.AbstractModel):
    _inherit = "ir.egress"

    @api.model
    def _prepare_session(self, session, *, purpose, policy):
        self.env["gateway.ml.policy"]._check_allowed(self.env.company, purpose)
        super()._prepare_session(session, purpose=purpose, policy=policy)
