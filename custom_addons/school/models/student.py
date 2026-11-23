from odoo import api,fields, models

class Student(models.Model):
    _name = "wb.student"
    _description = "This is Student Profile"

    name = fields.Char("Name")
    image = fields.Image("Student Image" ,max_width=256, max_height=256)
    product_id = fields.Many2one('product.product', string='Product')
    product_category = fields.Many2one(related='product_id.categ_id', string='Product Category', store=True)
    product_sales_price = fields.Float(related='product_id.lst_price', string='Product Sales Price', store=True)
    discounted_price = fields.Float(string='Discounted Price', compute='_compute_discounted_price', store = True)
    currency_id = fields.Many2one('res.currency', string='Currency')
    amount = fields.Monetary("Amount", currency_field='currency_id')
    name1 = fields.Char("student of the first")
    name2= fields.Char(string="Student of the second", default="Second", readonly=True)
    name3 = fields.Char("Name3")
    name4 = fields.Char("Name4")
    address = fields.Text("Address")
    address_html = fields.Html()
    level = fields.Selection([
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('higher', 'Higher Education')
    ])
    attachments = fields.Many2many('ir.attachment', string="Attachments")


    def _compute_discounted_price(self):
        for record in self:
            record.discounted_price = record.product_sales_price - 10


    def custom_method(self):
        print("Clicked the button")

        data = [{'name': 'New Student 1', 'address': 'what a day!'}, {'name': 'New Student 2'}]

        self.env['wb.student'].create(data)




    def custom_search(self):
        environ = self.env['wb.student']
        rec = environ.search([])


    @api.model_create_multi
    def create(self,vals):
        print(self)
        print(vals)
        res = super(Student,self).create(vals)
        print(res)
        return res