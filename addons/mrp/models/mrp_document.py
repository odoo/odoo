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

    ir_attachment_id = fields.Many2one('ir.attachment', string='Related attachment', required=True, ondelete='cascade')
    active = fields.Boolean('Active', default=True)
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Very High')], string="Priority", help='Gives the sequence order when displaying a list of MRP documents.')

    def unlink(self):
        self.mapped('ir_attachment_id').unlink()
        return super(MrpDocument, self).unlink()
