from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SifnextRKA(models.Model):
    _name = "sifnext.rka"
    _description = "Rencana Kerja dan Anggaran"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "year desc, unit_id, account_id"

    name = fields.Char(compute="_compute_name", store=True)
    unit_id = fields.Many2one(
        "sifnext.unit", required=True, index=True, tracking=True,
        domain="[('company_id', '=', company_id)]",
    )
    year = fields.Integer(required=True, default=lambda self: fields.Date.today().year, index=True, tracking=True)
    account_id = fields.Many2one(
        "account.account", string="COA", required=True, index=True, tracking=True,
        domain="[('company_ids', 'in', company_id)]",
    )
    budget_amount = fields.Monetary(required=True, tracking=True)
    realization_amount = fields.Monetary(compute="_compute_realization", store=True)
    remaining_amount = fields.Monetary(compute="_compute_realization", store=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    state = fields.Selection(
        [("draft", "Draft"), ("approved", "Disetujui"), ("closed", "Ditutup")],
        required=True, default="draft", tracking=True, index=True,
    )
    realization_ids = fields.One2many("sifnext.rka.realization", "rka_id", string="Realisasi", readonly=True)

    _scope_uniq = models.Constraint(
        "unique (company_id, unit_id, year, account_id)",
        "RKA untuk perusahaan, unit, tahun, dan COA yang sama sudah tersedia.",
    )
    _budget_positive = models.Constraint(
        "CHECK (budget_amount > 0)",
        "Nilai anggaran harus lebih dari nol.",
    )

    @api.depends("unit_id.code", "year", "account_id.code")
    def _compute_name(self):
        for record in self:
            parts = [record.unit_id.code, str(record.year or ""), record.account_id.code]
            record.name = " / ".join(part for part in parts if part)

    @api.depends("budget_amount", "realization_ids.amount")
    def _compute_realization(self):
        for record in self:
            record.realization_amount = sum(record.realization_ids.mapped("amount"))
            record.remaining_amount = record.budget_amount - record.realization_amount

    @api.constrains("year", "unit_id", "account_id", "company_id")
    def _check_scope(self):
        for record in self:
            if record.year < 2000 or record.year > 9999:
                raise ValidationError(_("Tahun RKA harus terdiri dari empat digit."))
            if record.unit_id.company_id != record.company_id:
                raise ValidationError(_("Unit RKA harus berasal dari perusahaan yang sama."))
            if record.company_id not in record.account_id.company_ids:
                raise ValidationError(_("COA RKA harus tersedia untuk perusahaan yang sama."))

    def write(self, vals):
        protected = {"unit_id", "year", "account_id", "company_id", "budget_amount"}
        if protected.intersection(vals) and any(record.state != "draft" for record in self):
            raise UserError(_("RKA hanya dapat diubah saat Draft."))
        return super().write(vals)

    def unlink(self):
        if any(record.state != "draft" or record.realization_ids for record in self):
            raise UserError(_("Hanya RKA Draft tanpa realisasi yang dapat dihapus."))
        return super().unlink()

    def action_approve(self):
        self.write({"state": "approved"})

    def action_close(self):
        if any(record.state != "approved" for record in self):
            raise UserError(_("Hanya RKA Disetujui yang dapat ditutup."))
        self.write({"state": "closed"})

    def action_reset_draft(self):
        if any(record.realization_ids for record in self):
            raise UserError(_("RKA yang sudah memiliki realisasi tidak dapat dikembalikan ke Draft."))
        self.write({"state": "draft"})


class SifnextRKARealization(models.Model):
    _name = "sifnext.rka.realization"
    _description = "Realisasi RKA"
    _order = "realization_date desc, id desc"

    rka_id = fields.Many2one("sifnext.rka", required=True, ondelete="restrict", index=True)
    ppl_id = fields.Many2one("sifnext.ppl", required=True, ondelete="restrict", index=True)
    ppl_line_id = fields.Many2one("sifnext.ppl.line", required=True, ondelete="restrict", index=True)
    event_key = fields.Char(required=True, index=True)
    realization_date = fields.Date(required=True)
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one(related="rka_id.currency_id", store=True)
    company_id = fields.Many2one(related="rka_id.company_id", store=True, index=True)

    _event_line_uniq = models.Constraint(
        "unique (event_key, ppl_line_id)",
        "Realisasi detail PPL ini sudah tercatat.",
    )
    _amount_positive = models.Constraint("CHECK (amount > 0)", "Nilai realisasi harus lebih dari nol.")

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("rka_realization_hook"):
            raise UserError(_("Realisasi RKA hanya dapat dibuat melalui konfirmasi pembayaran PPL."))
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(_("Realisasi RKA tidak dapat diubah."))

    def unlink(self):
        raise UserError(_("Realisasi RKA tidak dapat dihapus."))
