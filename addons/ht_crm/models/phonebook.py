from odoo import models, fields, api, exceptions
import datetime
import random

class PhoneBook(models.Model):
    _name = 'sale.phonebook'
    _description = 'DATA danh bạ'

    # Trường cơ bản
    name = fields.Char(string="Chủ thuê bao")
    phone = fields.Char(string="Số điện thoại", required=True)
    note = fields.Text(string="Ghi chú")
    
    # Trường bổ sung
    salesperson_id = fields.Many2one(
        'sale.employee',
        string="Sales phụ trách",
        domain=[('role_ids.code', '=', 'sales')]
    )

    previous_salesperson_ids = fields.Many2many(
        'sale.employee',
        string="Lịch sử phụ trách",
        groups="ht_crm.group_ht_executive"
    )

    project_id = fields.Many2one(
        "estate.project",
        string="Dự án"
    )
    status = fields.Selection([
        ('new', 'Chưa gọi'),
        ('called', 'Đã gọi'),
        ('invalid', 'Số không hợp lệ / Hủy')
    ], string="Trạng thái", default='new', store=True)

    # Trường xử lý số nóng lạnh.    
    is_hot = fields.Boolean(string="Nóng?", default=False)
    hot_until = fields.Datetime(string="Hết hạn Data Nóng")
    hot_duration = fields.Integer(
        string="Thời gian Data Nóng (phút)",
        default=30
    )

    @api.constrains('phone')
    def _check_phone_unique(self):
        for rec in self:
            if not rec.phone:
                continue

            existing = self.search([
                ('id', '!=', rec.id),
                ('phone', '=', rec.phone),
            ], limit=1)

            if existing:
                raise exceptions.ValidationError(
                    f"Số điện thoại đã tồn tại "
                    f"trong dự án: {existing.project_id.name}"
                )


    def write(self, vals):
        status_dict = dict(self._fields['status'].selection)

        old_status_map = {
            rec.id: rec.status
            for rec in self
        }

        res = super().write(vals)

        for rec in self:

            # Hot logic
            if 'is_hot' in vals and vals['is_hot']:
                rec.set_expire_on_hot()

            # Status logging
            if 'status' in vals:
                old_status = old_status_map.get(rec.id)

                if old_status != rec.status:
                    old_label = status_dict.get(old_status)
                    new_label = status_dict.get(rec.status)

                    self.env['sale.phonebook.log'].create({
                        'phonebook_id': rec.id,
                        'action': 'status_changed',
                        'note': f'{old_label} -> {new_label}'
                    })

        return res

    def set_expire_on_hot(self):
        for rec in self:
            rec.hot_until = fields.Datetime.now() + datetime.timedelta(
                minutes=rec.hot_duration or 30
            )


    # Hàm phân KH (ngẫu nhiên)
    def action_distribute_numbers(self):
        eligible_users = self.env['sale.employee'].search([
            ('active', '=', True),
            ('role_ids.code', '=', 'sales')
        ])

        if not eligible_users:
            raise Exception("No active users found.")

        # Với mọi record đang được chọn.
        for record in self:
            # Dữ liệu rác
            if record.status == 'invalid':
                continue

            available = eligible_users.filtered(
                lambda u: u not in record.previous_salesperson_ids
            )

            if not available:
                record.write({'salesperson_id': ""})
                record.write({'previous_salesperson_ids': [(5, 0, 0)]})
                continue

            assigned_user = random.choice(available)

            record.salesperson_id = assigned_user.id
            record.previous_salesperson_ids = [(4, assigned_user.id)]
    
class PhoneBookLog(models.Model):
    _name = "sale.phonebook.log"
    _description = "Log thao tác"
    _order = "create_date desc"

    phonebook_id = fields.Many2one(
        "sale.phonebook",
        required=True,
        ondelete="cascade"
    )

    user_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user
    )

    action = fields.Char(required=True)

    note = fields.Text()