from odoo import fields, models


class BrEfdContribWizard(models.TransientModel):
    _name = "br.efd.contrib.wizard"
    _description = "Wizard EFD Contribuicoes"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    period_from = fields.Date(required=True)
    period_to = fields.Date(required=True)

    def action_generate(self):
        self.ensure_one()
        from ..efd_contrib.br_efd_contrib import BrEfdContrib

        writer = BrEfdContrib(self.company_id, self.period_from, self.period_to)
        return writer.build_blocks()

