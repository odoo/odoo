from odoo import models, fields, api, exceptions

class PhoneBook(models.Model):
    _name = 'sale.phonebook'
    _description = 'Sales Phonebook for Managing Customer Contacts'

    customer_id = fields.Many2one(
        'sale.customer',
        string="Tên KH",
        ondelete='cascade', # Sửa thành restrict sau
        store=True
    )

    # interaction_ids = fields.One2many(
    #     'sale.phonebook.interaction',
    #     'phone_id',
    #     string="Interactions"
    # )

    phone = fields.Char(string="SĐT")
    is_called = fields.Boolean(string="Đã gọi?", default=False, store=True)
    unreachable = fields.Boolean(string="Cúp máy?", default=False, store=True)
    note = fields.Text(string="Ghi chú")
    is_primary = fields.Boolean(string="Số chính")


    _sql_constraints = [
        ('unique_phone', 'unique(phone)', 'Phone number already exists!')
    ]

    @api.constrains('is_primary', 'customer_id')
    def _check_unique_primary(self):
        for rec in self:
            if rec.is_primary and rec.customer_id:
                if self.search_count([
                    ('customer_id', '=', rec.customer_id.id),
                    ('is_primary', '=', True),
                    ('id', '!=', rec.id)
                ]):
                    raise exceptions.ValidationError("Mỗi khách hàng chỉ được chọn 1 số chính!")
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            customer_id = vals.get('customer_id')
            if customer_id:
                existing_primary = self.search([
                    ('customer_id', '=', customer_id),
                    ('is_primary', '=', True)
                ], limit=1)

                # nếu chưa có primary thì record đầu tiên = primary
                if not existing_primary:
                    vals['is_primary'] = True
                else:
                    vals['is_primary'] = False

        return super().create(vals_list)
    
    def set_primary(self):
        for rec in self:
            self.search([
                ('customer_id', '=', rec.customer_id.id),
                ('id', '!=', rec.id)
            ]).write({'is_primary': False})

            rec.is_primary = True
                
class PhoneInteraction(models.Model):
    _name = 'sale.phonebook.interaction'
    _description = 'Phone Call / Interaction History'

    phone_id = fields.Many2one(
        'sale.phonebook',
        required=True,
        ondelete='cascade'
    )
    employee_id = fields.Many2one('res.users', required=True)

    action = fields.Selection([
        ('call', 'Call'),
        ('note', 'Add Note'),
        ('status', 'Status Change'),
    ], required=True)

    result = fields.Selection([
        ('success', 'Reached'),
        ('no_answer', 'No Answer'),
        ('rejected', 'Rejected'),
    ])

    note = fields.Text()
    timestamp = fields.Datetime(default=fields.Datetime.now)
    