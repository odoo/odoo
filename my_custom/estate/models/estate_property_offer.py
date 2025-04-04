from odoo import api, models, fields
from datetime import timedelta
from odoo.exceptions import UserError


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Real Estate Property Offer"
    _order = "price desc"

    price = fields.Float()

    _sql_constraints = [
        ("check_offer_price", "CHECK(price > 0)", "Price must be strictly positive")
    ]
    status = fields.Selection(
        selection=[
          ('accepted', 'Accepted'),
          ('refused', 'Refused'),
        ])
    partner_id = fields.Many2one("res.partner", required=True)
    property_id = fields.Many2one("estate.property", required=True)
    property_state = fields.Selection(related="property_id.status", store=True, string="Property State")
    validity = fields.Integer(string="Validity (days)", default=7)
    date_deadline = fields.Date(string="Deadline", compute="_compute_date_deadline", inverse="_inverse_date_deadline")

    # một type chỉ có 1 offer nhưng có thể offer nhiiều type
    # related field là trường hợp đặc biệt của compute field
    property_type_id = fields.Many2one(related="property_id.property_type_id", store=True)

    @api.depends("validity", "create_date")
    def _compute_date_deadline(self):
        for record in self:
            create_date = record.create_date or fields.Date.today()  # tạo một biến với fallback
            record.date_deadline = create_date + timedelta(days=record.validity)

    def _inverse_date_deadline(self):
        for record in self:
            create_date = (record.create_date or fields.Date.today()).date()
            if record.date_deadline:
                delta = record.date_deadline - create_date
                record.validity = delta.days

    def action_accept(self):
        for record in self:
            # nếu có người mua rồi
            if record.property_id.buyer_id:
                raise UserError("An offer has already been accepted for this property!")
            # nếu bị canceled
            elif record.property_id.status == "canceled":
                raise UserWarning("Canceled properties cannot be sold!") 
            record.status = "accepted"
            record.property_id.status = "offer_accepted"
            record.property_id.buyer_id = record.partner_id
            record.property_id.selling_price = record.price
        return True

    def action_refuse(self):
        for record in self:
            record.status = "refused"
        return True
    
    @api.model_create_multi
    # Hàm sẽ được gọi nếu như có thay đổi cấp model
    # Không thể đặt tên khác
    def create(self, vals):
        # self trong một phương thức của class luôn đại diện cho bản thân class đó.
        # vals là 1 mảng các Dict

        result = self.env[self._name]  # Tạo một recordset rỗng để lưu kết quả
        
        for record in vals:
            property_id = record.get("property_id")
            price = record.get("price")

            if property_id and price:
                # lấy Instance của property mà thằng offer đang yêu cầu
                property_instance = self.env["estate.property"].browse(property_id)

                # Tìm các existing offer
                existing_offers = self.search([("property_id", "=", property_id)])
                # Xét điều kiện existing offer để tránh lỗi value
                if existing_offers and min(existing_offers.mapped("price")) > price:
                    raise UserError("Cannot create an offer lower than an existing one!")
                
                property_instance.status = "offer_received"
                
            created_record = super().create(record)
            result += created_record
        
        return result
