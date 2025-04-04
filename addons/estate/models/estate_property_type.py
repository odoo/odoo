from odoo import api, models, fields


class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Real Estate Property Type"
    _order = "sequence, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(string="Type", required=True)
    property_count = fields.Integer(string="Property Count", compute="_compute_property_count")
    property_ids = fields.One2many("estate.property", "property_type_id", string="Properties")
    offer_ids = fields.One2many('estate.property.offer', 'property_type_id')
    offer_count = fields.Integer(string="Offer count", compute="_compute_offer_count")
    _sql_constraints = [
        ("unique_type_name", "UNIQUE(name)", "Property type name must be unique")
    ]

    #theo dõi sự thay đổi của property_ids vì bất cứ thêm sửa xóa nào cũng gây thay đổi
    @api.depends("offer_ids")
    def _compute_offer_count(self):
        for record in self:
            # Tìm tất cả bất động sản có offer_id trùng với estate.property.type.id
            #  (Hiểu đơn giản là tìm số offer có type là record hiện tại)
            # record.offer_count = self.env["estate.property.offer"].search_count([('property_type_id', "=", record.id)])
            record.offer_count = len(record.offer_ids)
