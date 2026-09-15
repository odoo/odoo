from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResourceAssignment(models.Model):
    _inherit = "resource.assignment"

    department_id = fields.Many2one(
        comodel_name="hr.department",
        index="btree_not_null",
        ondelete="restrict",
        check_company=True,
        help="Who holds it when no one person does: a department.",
    )

    @api.depends("department_id.name")
    def _compute_name(self):
        return super()._compute_name()

    def _get_holder_name(self):
        return super()._get_holder_name() or self.department_id.name

    def _has_holder(self):
        return super()._has_holder() or bool(self.department_id)

    @api.constrains("resource_id", "assignee_id", "department_id")
    def _check_parties(self):
        for record in self:
            if record.assignee_id and record.department_id:
                raise ValidationError(
                    self.env._(
                        "%(resource)s is held by a person or by a department, not by both.",
                        resource=record.resource_id.name,
                    )
                )
        return super()._check_parties()
