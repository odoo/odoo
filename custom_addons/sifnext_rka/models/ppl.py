from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class SifnextPPL(models.Model):
    _inherit = "sifnext.ppl"

    budget_total = fields.Monetary(compute="_compute_budget_summary")
    budget_realization = fields.Monetary(compute="_compute_budget_summary")
    budget_remaining = fields.Monetary(compute="_compute_budget_summary")

    @api.depends(
        "line_ids.rka_id", "line_ids.rka_id.budget_amount",
        "line_ids.rka_id.realization_amount", "line_ids.rka_id.remaining_amount",
    )
    def _compute_budget_summary(self):
        for record in self:
            rkas = record.line_ids.rka_id
            record.budget_total = sum(rkas.mapped("budget_amount"))
            record.budget_realization = sum(rkas.mapped("realization_amount"))
            record.budget_remaining = sum(rkas.mapped("remaining_amount"))

    def _prepare_budget_check_payload(self):
        payload = super()._prepare_budget_check_payload()
        payload["lines"] = [{
            **line_payload,
            "rka_id": self.line_ids.browse(line_payload["line_id"]).rka_id.id,
        } for line_payload in payload["lines"]]
        return payload

    def _prepare_integration_payload(self):
        payload = super()._prepare_integration_payload()
        lines_by_id = {line.id: line for line in self.line_ids}
        for item in payload["ppl"]["lines"]:
            rka = lines_by_id[item["id"]].rka_id
            item["rka"] = {
                "id": rka.id,
                "name": rka.name,
                "year": rka.year,
            } if rka else None
        return payload

    def _validate_rka_budget(self, payload):
        super()._validate_rka_budget(payload)
        totals = defaultdict(float)
        rka_model = self.env["sifnext.rka"]
        for item in payload["lines"]:
            if not item.get("account_id") or not item.get("rka_id"):
                raise ValidationError(_("COA dan RKA wajib diisi pada seluruh detail sebelum verifikasi."))
            totals[item["rka_id"]] += item["amount"]

        # Serialize checks for the same budget rows to prevent concurrent overspending.
        rka_ids = sorted(totals)
        self.env.cr.execute("SELECT id FROM sifnext_rka WHERE id IN %s FOR UPDATE", [tuple(rka_ids)])
        rkas = {rka.id: rka for rka in rka_model.browse(rka_ids).exists()}
        request_year = fields.Date.to_date(payload["request_date"]).year
        for rka_id, requested in totals.items():
            rka = rkas.get(rka_id)
            if not rka:
                raise ValidationError(_("RKA yang dipilih tidak tersedia."))
            if rka.state != "approved":
                raise ValidationError(_("RKA %s belum disetujui.") % rka.display_name)
            if rka.company_id.id != payload["company_id"] or rka.unit_id.id != payload["unit_id"]:
                raise ValidationError(_("RKA %s tidak sesuai dengan perusahaan atau Unit PPL.") % rka.display_name)
            if rka.year != request_year:
                raise ValidationError(_("RKA %s tidak sesuai dengan tahun pengajuan.") % rka.display_name)
            account_ids = {
                item["account_id"] for item in payload["lines"] if item["rka_id"] == rka_id
            }
            if account_ids != {rka.account_id.id}:
                raise ValidationError(_("COA detail tidak sesuai dengan mapping RKA %s.") % rka.display_name)
            if requested > rka.remaining_amount:
                raise ValidationError(_(
                    "Anggaran RKA %(rka)s tidak cukup. Tersedia %(available)s, diminta %(requested)s."
                ) % {"rka": rka.display_name, "available": rka.remaining_amount, "requested": requested})
        return True

    def _notify_rka_paid(self, payload):
        super()._notify_rka_paid(payload)
        event_key = payload["idempotency_key"]
        # Realizations are immutable system journals. Elevate only this model operation
        # after the PPL workflow and budget validations have succeeded.
        realization_model = self.env["sifnext.rka.realization"].sudo().with_context(
            rka_realization_hook=True,
        )
        existing_lines = set(realization_model.search([
            ("event_key", "=", event_key),
        ]).mapped("ppl_line_id").ids)
        values = []
        for line in self.line_ids:
            if line.id not in existing_lines:
                values.append({
                    "rka_id": line.rka_id.id,
                    "ppl_id": self.id,
                    "ppl_line_id": line.id,
                    "event_key": event_key,
                    "realization_date": self.payment_date,
                    "amount": line.subtotal,
                })
        if values:
            realization_model.create(values)
        return True


class SifnextPPLLine(models.Model):
    _inherit = "sifnext.ppl.line"

    ppl_unit_id = fields.Many2one(related="ppl_id.unit_id")
    request_year = fields.Integer(compute="_compute_request_year")
    rka_id = fields.Many2one(
        "sifnext.rka", string="RKA", index=True,
        domain="[('company_id', '=', company_id), ('unit_id', '=', ppl_unit_id), "
               "('year', '=', request_year), ('account_id', '=', account_id), "
               "('state', '=', 'approved')]",
    )
    budget_available = fields.Monetary(related="rka_id.remaining_amount", readonly=True)

    @api.depends("ppl_id.request_date")
    def _compute_request_year(self):
        for line in self:
            line.request_year = line.ppl_id.request_date.year if line.ppl_id.request_date else False

    @api.onchange("account_id")
    def _onchange_account_id(self):
        result = super()._onchange_account_id()
        self.rka_id = False
        if self.account_id and self.ppl_id.unit_id and self.ppl_id.request_date:
            candidates = self.env["sifnext.rka"].search([
                ("company_id", "=", self.ppl_id.company_id.id),
                ("unit_id", "=", self.ppl_id.unit_id.id),
                ("year", "=", self.ppl_id.request_date.year),
                ("account_id", "=", self.account_id.id),
                ("state", "=", "approved"),
            ], limit=2)
            if len(candidates) == 1:
                self.rka_id = candidates
        return result

    def _check_finance_rka_access(self, vals):
        if "rka_id" not in vals:
            return
        if not self.env.user.has_group("sifnext_ppl.group_ppl_finance"):
            raise AccessError(_("Hanya Finance yang dapat memilih atau mengubah RKA."))
        if any(line.ppl_id.state not in ("draft", "submitted") for line in self):
            raise UserError(_("RKA hanya dapat diubah sebelum PPL diverifikasi."))

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get("rka_id") for vals in vals_list) and not self.env.user.has_group("sifnext_ppl.group_ppl_finance"):
            raise AccessError(_("Hanya Finance yang dapat memilih RKA."))
        return super().create(vals_list)

    def write(self, vals):
        self._check_finance_rka_access(vals)
        if "account_id" in vals and "rka_id" not in vals:
            vals = dict(vals, rka_id=False)
        return super().write(vals)
