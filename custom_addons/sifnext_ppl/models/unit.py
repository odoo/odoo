from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SifnextUnit(models.Model):
    _name = "sifnext.unit"
    _description = "Unit Organisasi"
    _order = "code, name"

    name = fields.Char(string="Nama Unit", required=True)
    code = fields.Char(string="Kode Unit", required=True, index=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    _code_company_uniq = models.Constraint(
        "unique (code, company_id)",
        "Kode Unit harus unik dalam satu perusahaan.",
    )

    journal_unit_dept = fields.Selection(
        [("tpa", "TPA"), ("sd", "SD"), ("smp", "SMP"), ("sma", "SMA"),
         ("univ", "Universitas"), ("pusat", "Yayasan / Kantor Pusat")],
        string="Unit Jurnal", default="pusat", required=True,
        help="Mapping unit ke kolom Unit/Departemen pada Jurnal Besar.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code"):
                vals["code"] = vals["code"].strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("code"):
            vals["code"] = vals["code"].strip().upper()
        return super().write(vals)

    @api.constrains("code")
    def _check_code(self):
        for unit in self:
            if not unit.code or not unit.code.replace("-", "").isalnum():
                raise ValidationError(_("Kode Unit hanya boleh berisi huruf, angka, dan tanda hubung."))


class ResUsers(models.Model):
    _inherit = "res.users"

    unit_id = fields.Many2one(
        "sifnext.unit",
        string="Unit",
        domain="[('company_id', 'in', company_ids)]",
    )
