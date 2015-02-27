from openerp import models, fields, api


class SaleCouponProgram(models.Model):
    _name = 'sale.couponprogram'
    _description = "Sales Coupon Program"

    program_name = fields.Char(string="Name", help="Program name")
    program_code = fields.Char(string="Code", help="Unique code to provide the reward")
    program_type = fields.Selection([('apply immediately', 'Apply Immediately'), ('public unique code',
                                     'Public Unique Code'), ('generated coupon', 'Generated Coupon')],
                                    string="Program Type", help="The type of the coupon program")
    is_program_active = fields.Boolean(string="Active", default=True, help="Coupon program is active or inactive")
    program_sequence = fields.Integer(string="Sequence", help="According to sequence, one rule is selected from multiple defined rules to apply")
    #coupon_ids = fields.One2many('WebsiteSaleCoupon.SaleCoupon', string="Coupon Id")
    #applicability_id = fields.Many2one('WebsiteSaleCoupon.SaleApplicability', string="Applicability Id")
    #reward_id = fields.Many2one('WebsiteSaleCoupon.SaleReward', string="Reward Id")
