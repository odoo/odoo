# ©  2008-2019 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    sequence_id = fields.Many2one("ir.sequence", string="Code Sequence")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    default_code = fields.Char(default="/")

    # doto de adaugat o constingere ca default_code si active sa fie unic

    def button_new_code(self):
        self.ensure_one()
        if not self.default_code or self.default_code == "/" or self.default_code == "auto":
            if self.categ_id.sequence_id:
                default_code = self.categ_id.sequence_id.next_by_id()
                self.write({"default_code": default_code})


class ProductProduct(models.Model):
    _inherit = "product.product"

    def button_new_code(self):
        self.ensure_one()
        if not self.default_code or self.default_code == "/" or self.default_code == "auto":
            if self.categ_id.sequence_id:
                default_code = self.categ_id.sequence_id.next_by_id()
                self.write({"default_code": default_code})
