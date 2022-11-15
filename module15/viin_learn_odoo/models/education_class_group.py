from odoo import fields, models, api
from odoo.exceptions import ValidationError


class EductionClassGroup(models.Model):
    _name = 'education.class.group'
    _description = 'Education Class Group'
    name = fields.Char(string='Name', translate=True, required=True)
    parent_id = fields.Many2one('education.class.group', string='Parent Group', ondelete='restrict')
    child_ids = fields.One2many('education.class.group', string='Child Groups', ondelete='restrict')
    _parent_store = True
    _parent_name = "parent_id" # tùy chọn nếu trường là cấp cha
    
    parent_path = fields.Char(index=True)
    @api.constrains('parent_id')
    def _check_hierarchy(self):
        if not self._check_recursion():
            raise ValidationError('Error! You cannot create recursivecategories.')