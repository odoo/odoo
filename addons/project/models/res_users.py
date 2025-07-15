from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    favorite_project_ids = fields.Many2many('project.project', 'project_favorite_user_rel', 'user_id', 'project_id',
                                            string='Favorite Projects', export_string_translation=False, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self._onboard_users_into_project(res)
        return res

    def write(self, vals):
        non_internal_users = self.filtered("share")
        res = super().write(vals)
        if "group_ids" in vals and non_internal_users:
            self.with_context(onboarding_from_write=True)._onboard_users_into_project(non_internal_users)
        return res

    def _onboard_users_into_project(self, users):
        if (internal_users := users.filtered(lambda u: not u.share)):
            ProjectTaskTypeSudo = self.env["project.task.type"].sudo()
            if self.env.context.get("onboarding_from_write"):
                user_person_stage_read_group = ProjectTaskTypeSudo._read_group(
                    domain=[("user_id", "in", internal_users.ids)],
                    groupby=["user_id"],
                    aggregates=["__count"],
                )

                users_with_stages = self.env["res.users"].concat(*[group[0] for group in user_person_stage_read_group])
                missing_users = internal_users - users_with_stages
            else:
                missing_users = internal_users

            if missing_users:
                create_vals = []
                for user in missing_users:
                    vals = self.env["project.task"].with_context(lang=user.lang)._get_default_personal_stage_create_vals(user.id)
                    create_vals.extend(vals)

                if create_vals:
                    ProjectTaskTypeSudo.with_context(default_project_id=False).create(create_vals)

                    return missing_users
