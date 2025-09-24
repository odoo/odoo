from odoo import models, fields, api
from odoo.exceptions import UserError

class VersioningMixin(models.AbstractModel):
    _name = "mail.versioning.mixin"
    _description = "Mixin to add versioning to a model"

    version_seq = fields.Char(string="Version from sequence", store=True, readonly=True, default=1)
    version = fields.Integer(
        string="Version", compute="_compute_version", store=False, readonly=True
    )

    @api.model
    def _get_sequence_name(self):
        return f"Version for model {self._name}"

    @api.model
    def _get_versioning_sequence(self):
        return self.env["ir.sequence"].search(
            [("name", "=", self._get_sequence_name())], limit=1
        )

    def write(self, vals):
        if 'version' in vals:
            raise UserError("Directly setting the version field is not allowed")
        if not (sequence := self._get_versioning_sequence()):
            sequence = self.env["ir.sequence"].sudo().create({
                "name": self._get_sequence_name(),
                "number_increment": 1,
                "number_next": 2,
            })
        vals['version_seq'] = sequence.next_by_id()
        return super().write(vals)

    @api.depends('version_seq')
    def _compute_version(self):
        for record in self:
            record.version = int(record.version_seq)
