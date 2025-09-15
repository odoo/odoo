from odoo import fields, models, Command


class TalentPoolAddApplicants(models.TransientModel):
    _name = "talent.pool.add.applicants"
    _description = "Add applicants to talent pool"
    applicant_ids = fields.Many2many(
        "hr.applicant",
        string="Applicants",
        required=True,
        domain=[
            "|",
            ("talent_pool_ids", "!=", False),
            ("is_applicant_in_pool", "=", False),
        ],
    )
    talent_pool_ids = fields.Many2many("hr.talent.pool", string="Talent Pool")
    categ_ids = fields.Many2many(
        "hr.applicant.category",
        string="Tags",
    )

    def _add_applicants_to_pool(self):
        talents = self.env["hr.applicant"]
        for applicant in self.applicant_ids:
            if applicant.talent_pool_ids:
                applicant.write(
                    {
                        "talent_pool_ids": [
                            Command.link(talent_pool.id)
                            for talent_pool in self.talent_pool_ids
                        ],
                        "categ_ids": [
                            Command.link(categ.id) for categ in self.categ_ids
                        ],
                    }
                )
                talents += applicant
            else:
                talent = applicant.with_context(no_copy_in_partner_name=True).copy(
                    {
                        "job_id": False,
                        "talent_pool_ids": self.talent_pool_ids,
                        "categ_ids": applicant.categ_ids + self.categ_ids,
                    }
                )
                talent.write({"pool_applicant_id": talent.id})
                applicant.write({"pool_applicant_id": talent.id})
                talents += talent
        return talents

    def action_add_applicants_to_pool(self):
        talents = self.sudo()._add_applicants_to_pool()
        if len(talents) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "hr.applicant",
                "view_mode": "form",
                "views": [
                    (
                        self.env.ref("hr_recruitment.hr_applicant_view_form").id,
                        "form",
                    )
                ],
                "target": "current",
                "res_id": talents.id,
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "soft_reload",
            }
