from odoo import fields, models


class TestPopulateProduct(models.Model):
    _name = 'test_populate.product'
    _description = 'Test Product for populate'

    name = fields.Char("Product Name", required=True)
    price = fields.Float("Price")
    cost = fields.Float("Cost")
    active = fields.Boolean("Active", default=True)
    description = fields.Text("Description")
    category = fields.Selection([
        ('electronics', 'Electronics'),
        ('clothing', 'Clothing'),
        ('books', 'Books'),
        ('home', 'Home & Garden'),
    ], string="Category")
    created_date = fields.Date("Created Date")
    updated_at = fields.Datetime("Updated At")
    stock_quantity = fields.Integer("Stock Quantity")
    is_featured = fields.Boolean("Is Featured")
    is_sellable = fields.Boolean("Is Product Sellable", required=True, default=True)
    supplier_id = fields.Many2one('test_populate.supplier', string="Supplier")
    tag_ids = fields.Many2many('test_populate.tag', string="Product Tags")
    currency_id = fields.Many2one('res.currency', string="Currency")
    monetary_price = fields.Monetary("Monetary Price", currency_field='currency_id')


class TestPopulateSupplier(models.Model):
    _name = 'test_populate.supplier'
    _description = 'Test Supplier for populate'

    name = fields.Char("Supplier Name", required=True)
    email = fields.Char("Email")
    phone = fields.Char("Phone")
    country_code = fields.Selection([
        ('US', 'United States'),
        ('CA', 'Canada'),
        ('GB', 'United Kingdom'),
        ('DE', 'Germany'),
        ('FR', 'France'),
    ], string="Country")
    rating = fields.Float("Rating")
    established_date = fields.Date("Established Date")
    is_active = fields.Boolean("Is Active", default=True)
    notes = fields.Text("Notes")
    product_ids = fields.One2many('test_populate.product', 'supplier_id', string="Products")
    warehouse_id = fields.Many2one('test_populate.warehouse', string="Warehouse")


class TestPopulateCustomer(models.Model):
    _name = 'test_populate.customer'
    _description = 'Test Customer for populate'

    name = fields.Char("Customer Name", required=True)
    first_name = fields.Char("First Name")
    last_name = fields.Char("Last Name")
    email = fields.Char("Email", required=True)
    phone = fields.Char("Phone")
    age = fields.Integer("Age")
    birth_date = fields.Date("Birth Date")
    registration_date = fields.Datetime("Registration Date")
    is_vip = fields.Boolean("VIP Customer")
    preferred_category = fields.Selection([
        ('electronics', 'Electronics'),
        ('clothing', 'Clothing'),
        ('books', 'Books'),
        ('home', 'Home & Garden'),
    ], string="Preferred Category")
    total_spent = fields.Float("Total Spent")
    notes = fields.Text("Customer Notes")


class TestPopulateOrder(models.Model):
    _name = 'test_populate.order'
    _description = 'Test Order for populate'

    name = fields.Char("Order Reference", required=True)
    customer_id = fields.Many2one('test_populate.customer', string="Customer", required=True)
    order_date = fields.Date("Order Date", required=True)
    delivery_date = fields.Datetime("Delivery Date")
    total_amount = fields.Float("Total Amount")
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ], string="Status", default='draft')
    is_urgent = fields.Boolean("Urgent Order")
    notes = fields.Text("Order Notes")
    line_ids = fields.One2many('test_populate.order.line', 'order_id', string="Order Lines")


class TestPopulateOrderLine(models.Model):
    _name = 'test_populate.order.line'
    _description = 'Test Order Line for populate'

    order_id = fields.Many2one('test_populate.order', string="Order", required=True)
    product_id = fields.Many2one('test_populate.product', string="Product", required=True)
    quantity = fields.Integer("Quantity", default=1)
    unit_price = fields.Float("Unit Price")
    total_price = fields.Float("Total Price", compute='_compute_total_price', store=True)

    def _compute_total_price(self):
        for line in self:
            line.total_price = line.quantity * line.unit_price


class TestPopulateTag(models.Model):
    _name = 'test_populate.tag'
    _description = 'Test Tag for populate'

    name = fields.Char("Tag Name", required=True)
    color = fields.Integer("Color Index")


class TestPopulateProductWithTags(models.Model):
    _name = 'test_populate.product.tagged'
    _description = 'Test Product with Tags for populate'

    name = fields.Char("Product Name", required=True)
    price = fields.Float("Price")
    tag_ids = fields.Many2many('test_populate.tag', string="Tags")


class TestPopulateWarehouse(models.Model):
    _name = 'test_populate.warehouse'
    _description = 'Test Warehouse for populate'

    name = fields.Char("Warehouse Name", required=True)
    location = fields.Char("Location")
    supplier_ids = fields.One2many('test_populate.supplier', 'warehouse_id', string="Suppliers")


class TestPopulateReference(models.Model):
    _name = 'test_populate.reference'
    _description = 'Test Reference for populate'

    name = fields.Char("Reference Name", required=True)
    res_model = fields.Char("Model", required=True)
    res_id = fields.Many2oneReference("Record", model_field='res_model')
    reference = fields.Reference(
        selection=[
            ('test_populate.product', 'A Product'),
            ('test_populate.supplier', 'A Supplier'),
        ],
    )


class TestPopulateProject(models.Model):
    _name = 'test_populate.project'
    _description = 'Test Project for populate (with properties definition)'

    name = fields.Char("Project Name", required=True)
    attributes_definition = fields.PropertiesDefinition("Task Attributes Definition")


class TestPopulateTask(models.Model):
    _name = 'test_populate.task'
    _description = 'Test Task for populate (with properties)'

    name = fields.Char("Task Name", required=True)
    project_id = fields.Many2one('test_populate.project', string="Project", required=True)
    attributes = fields.Properties("Attributes", definition='project_id.attributes_definition')
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string="Priority")
