# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _


class IrAttachmentReport(models.Model):
    _name = "ir.attachment.report"
    _description = "Storage"
    _order = 'size desc'
    _auto = False

    res_model = fields.Char("Model", readonly=True)
    res_id = fields.Many2oneReference("Record", model_field='res_model', readonly=True)
    size = fields.Integer("Total Size")
    name = fields.Char('Resource Name', compute='_compute_name')

    def _compute_name(self):
        for attachment in self:
            if attachment.res_model and attachment.res_id:
                record = self.env[attachment.res_model].browse(attachment.res_id)
                attachment.name = record.display_name
            else:
                attachment.name = False

    @property
    def _table_query(self):
        return """
SELECT
    min(id) AS id,
    res_model,
    res_id,
    sum(file_size) AS size
FROM ir_attachment
WHERE
    type = 'binary'
    AND res_id > 0
    AND res_model IS NOT NULL
GROUP BY
    res_model,
    res_id
"""

    def action_attachment_detail(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "name": _('Storage Detail: %(name)s', name=self.name),
            "views": [[self.env.ref('data_cleaning.view_data_storage_attachment_tree').id, "list"]],
            "domain": [('id', '>', 0), ('res_id', '=', self.res_id), ('res_model', '=', self.res_model)],
        }
