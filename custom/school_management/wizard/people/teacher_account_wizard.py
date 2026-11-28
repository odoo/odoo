from odoo import _, fields, models
from odoo.exceptions import UserError


class UniversityTeacherAccountWizard(models.TransientModel):
    _name = "university.teacher.account.wizard"
    _description = "Create Teacher Login Accounts"

    teacher_ids = fields.Many2many(
        "university.teacher",
        string="Teachers",
        required=True,
        domain="[('email', '!=', False)]",
    )
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if "teacher_ids" in fields_list and not defaults.get("teacher_ids"):
            active_model = self.env.context.get("active_model")
            active_ids = self.env.context.get("active_ids") or []
            if active_model == "university.teacher" and active_ids:
                defaults["teacher_ids"] = [(6, 0, active_ids)]
        return defaults
    def action_create_accounts(self):
        self.ensure_one()
        if not self.env.user.has_group("school_management.group_school_admin"):
            raise UserError(_("Only University Administrators can create teacher login accounts."))

        teacher_group = self.env.ref("school_management.group_school_teacher")
        dashboard_group = self.env.ref("school_management.group_teacher_dashboard")
        internal_group = self.env.ref("base.group_user")
        Users = self.env["res.users"].sudo()

        created = []
        skipped = []

        for teacher in self.teacher_ids:
            email = (teacher.email or "").strip()
            if not email:
                raise UserError(_("Teacher %s has no email address.") % teacher.display_name)

            if teacher.user_id:
                teacher.user_id.sudo().write({
                    "group_ids": [
                        (4, internal_group.id),
                        (4, teacher_group.id),
                        (4, dashboard_group.id),
                    ],
                })
                skipped.append(_("%s: already linked to %s") % (teacher.display_name, teacher.user_id.login))
                continue

            existing_user = Users.search([("login", "=ilike", email)], limit=1)
            if existing_user:
                if existing_user.teacher_id and existing_user.teacher_id != teacher:
                    raise UserError(
                        _("Email %(email)s is already linked to another teacher: %(teacher)s.")
                        % {"email": email, "teacher": existing_user.teacher_id.display_name}
                    )
                existing_user.write({
                    "teacher_id": teacher.id,
                    "group_ids": [
                        (4, internal_group.id),
                        (4, teacher_group.id),
                        (4, dashboard_group.id),
                    ],
                })
                teacher.sudo().write({"user_id": existing_user.id})
                skipped.append(_("%s: linked existing user %s") % (teacher.display_name, email))
                continue

            user = Users.create({
                "name": teacher.name,
                "login": email,
                "email": email,
                "teacher_id": teacher.id,
                "group_ids": [(6, 0, [internal_group.id, teacher_group.id, dashboard_group.id])],
            })
            teacher.sudo().write({"user_id": user.id})
            created.append(email)
            user.with_context(create_user=1).action_reset_password()

        message_parts = []
        if created:
            message_parts.append(_("Created accounts: %s") % ", ".join(created))
        if skipped:
            message_parts.append(_("Skipped/linked: %s") % "; ".join(skipped))
        message = "\n".join(message_parts) or _("No teacher accounts were created.")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Teacher Accounts"),
                "message": message,
                "type": "success",
                "sticky": True,
            },
        }
