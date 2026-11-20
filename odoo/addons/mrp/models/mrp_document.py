# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MrpDocument(models.Model):
    """ Extension of ir.attachment only used in MRP to handle archivage
    and basic versioning.
    """
    _name = 'mrp.document'
    _description = "Production Document"
    _inherits = {
        'ir.attachment': 'ir_attachment_id',
    }
    _order = "priority desc, id desc"

    def copy(self, default=None):
        ir_default = default
        if ir_default:
            ir_fields = list(self.env['ir.attachment']._fields)
            ir_default = {field : default[field] for field in default.keys() if field in ir_fields}
        new_attach = self.ir_attachment_id.with_context(no_document=True).copy(ir_default)
        return super().copy(dict(default, ir_attachment_id=new_attach.id))

    ir_attachment_id = fields.Many2one('ir.attachment', string='Related attachment', required=True, ondelete='cascade')
    active = fields.Boolean('Active', default=True)
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Very High')], string="Priority") # used to order

    def unlink(self):
        self.mapped('ir_attachment_id').unlink()
        return super(MrpDocument, self).unlink()
