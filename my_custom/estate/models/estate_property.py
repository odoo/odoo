from odoo import api, models, fields, tools
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError


class EstateProperty(models.Model):
    # khi đặt _name nó sẽ kế thừa toàn bộ phương thức của models.Model
    _name = "estate.property"
    _description = "Real Estate Property"
    _order = "id desc"

    # @api.... là một decorator
    # @api.model là một decorator định nghĩa phương thức cấp model level, không phụ thuộc vào bản ghi cụ thể
    # ví dụ, khi tạo bản ghi thì làm gì, updaate thì làm gì
    # khác với depends và onchange, constrains...

    def write(self, vals):
        result = super().write(vals)    
        for record in self:
            # chỉ cập nhật nếu có thay đổi
            if record.offer_ids and record.status == "new":
                record.status = "offer_received"
            elif not record.offer_ids and record.status == "offer_received":
                record.status = "new"
            # if record.offer_ids.price < record.best_price:
            #     raise UserError 
        return result

    name = fields.Char(string="Title", required=True)
    description = fields.Text(string="Description")
    postcode = fields.Char(string="Postcode")
    date_availability = fields.Date(
        string="Available From",
        default=lambda self: date.today() + relativedelta(months=3))
    expected_price = fields.Float(string="Expected Price", required=True)

    _sql_constraints = [
        ("checked_selling_price", "CHECK(selling_price >= 0)", "Selling Price must be positive."),
        ("checked_expected_price", "CHECK(expected_price > 0)", "Expected Price must be strictly positive."),
    ]
    selling_price = fields.Float(string="Selling Price", readonly=True)

    # khi expected_price hoặc selling_price bị thay đổi thì sẽ gọi phương thức này
    @api.constrains('expected_price', "selling_price")
    def _check_selling_price(self):
        for record in self:
            # Bỏ qua nếu selling_price = 0 (chưa có offer, còn offer_price đã luôn Strictly Positive)
            if tools.float_is_zero(record.selling_price, precision_digits=2):
                continue
            
            # Giá bán không được thấp hơn giá kì vong
            min_valid_price = 0.9 * record.expected_price
            # Hàm compare trả về True nếu như a< b ngược lại false
            # Phải dùng các tool float vì 0.1+0.2 !=0.3 (==0.300000004)
            if tools.float_compare(record.selling_price, min_valid_price, precision_digits=2) == -1:
            # Hàm này trả về 1 nếu a>b, 0 nếu a==b và -1 nếu a<b
                raise ValidationError("The selling price cannot be lower than 90% of the expected price")

    best_price = fields.Float(string="Best Offer", compute="_compute_best_price")
    bedrooms = fields.Integer(string="Bedrooms", default=2)
    living_area = fields.Integer(string="Living Area (sqm)")
    facades = fields.Integer(string="Facades")
    garage = fields.Boolean(string="Has Garage")
    garden = fields.Boolean(string="Has Garden")
    garden_area = fields.Integer(string="Garden Area (sqm)")
    total_area = fields.Integer(string="Total Area (sqm)", compute="_compute_total_area")

    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    garden_orientation = fields.Selection(
        selection=[
            ("north", "North"),
            ("south", "South"),
            ("east", "East"),
            ("west", "West"),
        ],
        string="Garden Orientation",
    )

    @api.onchange("garden")
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = "north"
        else:
            self.garden_area = 0
            self.garden_orientation = False

    status = fields.Selection(
        selection=[
            ("new", "New"),
            ("offer_received", "Offer Received"),
            ("offer_accepted", "Offer Accepted"),
            ("sold", "Sold"),
            ("canceled", "Canceled"),
        ],
        default="new",
        readonly=True,
        store=True
    )
    active = fields.Boolean(string="Active", default=True)
    property_type_id = fields.Many2one("estate.property.type", string="Property Type")
    salesperson_id = fields.Many2one(
        "res.users",
        string="Salesperson",
        default=lambda self: self.env.user
    )
    buyer_id = fields.Many2one(
        "res.partner",
        string="Buyer",
        index=True,
        copy=False,
        readonly=True)
    tag_ids = fields.Many2many(
        "estate.property.tag",
        string="Tags")
    offer_ids = fields.One2many("estate.property.offer", "property_id", string="Offers")

    @api.depends("offer_ids")
    def _compute_best_price(self):
        for record in self:
            record.best_price = max(record.offer_ids.mapped("price"), default=0.0)

    def action_sold(self):
        for record in self:
            if record.status == "canceled":
                raise UserWarning("Canceled properties cannot be sold")  
            record.status = "sold"
        return True

    def action_cancel(self):
        for record in self:
            if record.status == "sold":
                raise UserError("Sold properties cannot be canceled")  
            record.status = "canceled"
        return True
    
    # Check prior to unlink()
    # Decorator này check điều kiện trước khi Unlink()
    # at_uninstall=False bỏ qua điều kiện khi gỡ cài đặt module
    # nếu không có, khi gỡ module sẽ bị lỗi do điều kiện ondelete
    @api.ondelete(at_uninstall=False)
    def _check_status_before_delete(self):
        for record in self:
            if record.status not in ['new', 'canceled']:
                raise UserError("Cannot delete this property!")

