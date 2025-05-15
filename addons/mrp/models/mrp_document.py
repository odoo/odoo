# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MrpDocument(models.Model):
    """ Extension of ir.attachment only used in MRP to handle archivage
    and basic versioning.
    """
    _name = 'mrp.document'
    _description = "Production Document"
    _inherits = {'ir.attachment': 'ir_attachment_id'}
    _order = "priority desc, id desc"

    ir_attachment_id = fields.Many2one('ir.attachment', string='Related attachment', required=True, ondelete='cascade')
    active = fields.Boolean('Active', default=True)
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Very High')], string="Priority")  # used to order

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        ir_defaults = {}
        if default:
            ir_defaults = {field: value for field, value in default.items()
                        if field in self.env['ir.attachment']._fields}
        for document, vals in zip(self, vals_list):
            vals["ir_attachment_id"] = document.ir_attachment_id.with_context(
                no_document=True,
                disable_product_documents_creation=True
            ).copy(ir_defaults).id
        return vals_list

    @api.ondelete(at_uninstall=False)
    def _unlink_linked_ir_attachment(self):
        self.ir_attachment_id.unlink()
