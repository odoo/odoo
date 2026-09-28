from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    department_ids = fields.One2many(
        "hr.department",
        "company_id",
        string="Departemen",
        domain="[('company_id', '=', id)]",
    )


class ResUsers(models.Model):
    _inherit = "res.users"

    department_id = fields.Many2one(
        "hr.department",
        string="Departemen",
        domain="[('company_id', 'in', company_ids)]",
        check_company=True,
        ondelete="restrict",
        help="Departemen default untuk transaksi SIFNEXT. Departemen harus berasal dari salah satu perusahaan yang diizinkan untuk pengguna.",
    )

    @api.constrains("department_id", "company_ids")
    def _check_department_allowed_company(self):
        for user in self:
            if user.department_id and user.department_id.company_id not in user.company_ids:
                raise ValidationError(_("The user's department must belong to one of the user's allowed companies."))
