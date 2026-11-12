from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

MESSAGE_MAX_LENGTH = 500


class Od19Recognition(models.Model):
    _name = "od19.recognition"
    _description = "Employee Recognition (Kudos)"
    _order = "published_date desc, id desc"
    _inherit = ["mail.thread"]

    author_id = fields.Many2one(
        "hr.employee",
        string="From",
        required=True,
        default=lambda self: self.env.user.employee_id,
        ondelete="cascade",
    )
    recipient_id = fields.Many2one(
        "hr.employee", string="To", required=True, ondelete="cascade"
    )
    badge_id = fields.Many2one("od19.recognition.badge", string="Badge")
    message = fields.Text(string="Message", required=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    published_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    is_public = fields.Boolean(default=True)

    @api.constrains("author_id", "recipient_id")
    def _check_not_self(self):
        for record in self:
            if record.author_id and record.author_id == record.recipient_id:
                raise ValidationError(_("You cannot give a Kudos to yourself."))

    @api.constrains("message")
    def _check_message_length(self):
        for record in self:
            if record.message and len(record.message) > MESSAGE_MAX_LENGTH:
                raise ValidationError(
                    _("Kudos message must be %s characters or fewer.")
                    % MESSAGE_MAX_LENGTH
                )

    @api.constrains("author_id")
    def _check_author_is_current_user(self):
        # Constraints are evaluated on a sudoed recordset, so ``self.env.su``
        # is always True here. ``sudo()`` preserves the acting user, therefore
        # the checks below rely on ``self.env.user`` and its groups.
        if self.env.user.has_group("od19_recognition.group_recognition_manager"):
            return
        employee = self.env.user.employee_id
        for record in self:
            if record.author_id != employee:
                raise ValidationError(
                    _("You can only give a Kudos as yourself.")
                )
