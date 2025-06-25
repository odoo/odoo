# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    grade_id = fields.Many2one('res.partner.grade', 'Partner Level', tracking=True)

    def write(self, values):
        old_grade = self.grade_id
        old_pricelist = self.specific_property_product_pricelist
        if values.get('grade_id'):
            grade = self.env['res.partner.grade'].browse(values['grade_id'])
            self.child_ids.grade_id = grade
            if grade.default_pricelist_id:
                pricelist = values.get('specific_property_product_pricelist') or values.get('property_product_pricelist')
                if pricelist and pricelist != grade.default_pricelist_id.id:
                    raise UserError(self.env._(
                        "You are trying to assign two different pricelists (one directly and one from grade (%(grade_name)s)).",
                        grade_name=grade.name,
                    ))
                else:
                    values['specific_property_product_pricelist'] = grade.default_pricelist_id.id
            elif old_grade.default_pricelist_id and old_grade.default_pricelist_id.id == old_pricelist.id:
                values['specific_property_product_pricelist'] = False
        return super().write(values)
