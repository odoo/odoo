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


class HrDepartment(models.Model):
    _inherit = "hr.department"

    sif_code = fields.Char(
        string="Kode Departemen",
        index=True,
        copy=False,
    )
    sif_journal_unit_dept = fields.Selection(
        [
            ("tpa", "TPA"),
            ("sd", "SD"),
            ("smp", "SMP"),
            ("sma", "SMA"),
            ("univ", "Universitas"),
            ("pusat", "Yayasan / Kantor Pusat"),
        ],
        string="Klasifikasi Unit Jurnal (Legacy)",
        default="pusat",
        required=True,
        help="Klasifikasi kompatibilitas jurnal lama; bukan pengganti nama atau kode departemen.",
    )

    _sif_code_company_unique = models.Constraint(
        "unique(company_id, sif_code)",
        "Kode departemen harus unik dalam satu perusahaan.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("sif_code"):
                vals["sif_code"] = vals["sif_code"].strip().upper()
            else:
                code = sequence.next_by_code("sifnext.department.code")
                if not code:
                    raise ValidationError(_("Sequence kode departemen belum dikonfigurasi."))
                vals["sif_code"] = code
            company_id = vals.get("company_id") or self.env.company.id
            if vals.get("parent_id") and not vals.get("company_id"):
                company_id = self.browse(vals["parent_id"]).company_id.id or company_id
            duplicate = self.search_count([
                ("company_id", "=", company_id),
                ("sif_code", "=", vals["sif_code"]),
            ])
            if duplicate:
                raise ValidationError(_("Kode departemen harus unik dalam satu perusahaan."))
        return super().create(vals_list)

    def write(self, vals):
        if "sif_code" in vals and vals["sif_code"]:
            vals["sif_code"] = vals["sif_code"].strip().upper()
        return super().write(vals)

    @api.constrains("sif_code")
    def _check_sif_code(self):
        for department in self:
            if not department.sif_code or not department.sif_code.replace("-", "").isalnum():
                raise ValidationError(_("Kode departemen wajib diisi dan hanya boleh berisi huruf, angka, serta tanda hubung."))
            duplicate = self.search_count([
                ("id", "!=", department.id),
                ("company_id", "=", department.company_id.id),
                ("sif_code", "=", department.sif_code),
            ])
            if duplicate:
                raise ValidationError(_("Kode departemen harus unik dalam satu perusahaan."))


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
                raise ValidationError(_("Departemen pengguna harus berasal dari salah satu perusahaan yang diizinkan."))
