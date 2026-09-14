from odoo import Command, fields, models


class TalentPoolAddApplicants(models.TransientModel):
    _name = "talent.pool.add.applicants"
    _description = "Add applicants to talent pool"
    applicant_ids = fields.Many2many(
        comodel_name="hr.applicant",
        string="Applicants",
        required=True,
        domain=[
            "|",
            ("talent_pool_ids", "!=", False),
            ("is_applicant_in_pool", "=", False),
        ],
    )
    talent_pool_ids = fields.Many2many(comodel_name="hr.talent.pool")
    categ_ids = fields.Many2many(
        comodel_name="hr.applicant.category",
        string="Tags",
    )

    def _add_applicants_to_pool(self):
        """Return the talent record of every applicant, creating it when needed.

        An applicant is either a talent already, or points at one, or needs one
        copied from it. The first two only need the pools and tags linked, so
        they are written as one batch rather than one write each.
        """
        pool_vals = {
            "talent_pool_ids": [
                Command.link(pool_id) for pool_id in self.talent_pool_ids.ids
            ],
            "categ_ids": [Command.link(categ_id) for categ_id in self.categ_ids.ids],
        }
        Applicant = self.env["hr.applicant"]
        existing_talents = Applicant
        without_talent = Applicant
        for applicant in self.applicant_ids:
            if applicant.talent_pool_ids:
                existing_talents |= applicant
            elif applicant.pool_applicant_id:
                existing_talents |= applicant.pool_applicant_id
            else:
                without_talent |= applicant
        if existing_talents:
            existing_talents.write(pool_vals)

        talents = existing_talents
        for applicant in without_talent:
            talent = applicant.with_context(no_copy_in_partner_name=True).copy(
                {
                    "job_id": False,
                    "talent_pool_ids": self.talent_pool_ids.ids,
                    "categ_ids": (applicant.categ_ids + self.categ_ids).ids,
                }
            )
            applicant.pool_applicant_id = talent
            talents |= talent
        return talents

    def action_add_applicants_to_pool(self):
        # Not `sudo()`: the applicants reach this wizard through the user's own
        # rights, but an applicant's `pool_applicant_id` can point at a talent
        # in a company the user cannot see, and running the whole operation as
        # superuser wrote to that talent -- adding a record the user cannot read
        # to a pool of their own company.
        talents = self._add_applicants_to_pool()
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
