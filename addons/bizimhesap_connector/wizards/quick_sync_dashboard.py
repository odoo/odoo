# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BizimHesapQuickSync(models.TransientModel):
    """Hızlı senkron paneli.

    Tek ekrandan bağlantı seçip hızlı sync aksiyonlarını tetikler.
    """

    _name = "bizimhesap.quick.sync"
    _description = "BizimHesap Quick Sync"

    backend_id = fields.Many2one(
        "bizimhesap.backend",
        string="BizimHesap Bağlantısı",
        required=True,
        domain=[("state", "=", "connected")],
    )
    date_from = fields.Date(string="Başlangıç Tarihi")
    date_to = fields.Date(string="Bitiş Tarihi")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        backend = self.env["bizimhesap.backend"].search(
            [
                ("state", "=", "connected"),
                ("active", "=", True),
            ],
            limit=1,
        )
        if backend:
            res["backend_id"] = backend.id
        return res

    # ──────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────

    def _ensure_backend(self):
        self.ensure_one()
        if not self.backend_id:
            raise UserError(_("Lütfen bir BizimHesap bağlantısı seçin."))
        return self.backend_id

    def _notify(self, title, message, level="success"):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": level,
                "sticky": False,
            },
        }

    # ──────────────────────────────────────────────────────────────
    # Actions
    # ──────────────────────────────────────────────────────────────

    def action_sync_partners(self):
        backend = self._ensure_backend()
        backend.action_sync_partners()
        return self._notify(_("Cari Senkron"), _("Cariler senkronize edildi."))

    def action_sync_products(self):
        backend = self._ensure_backend()
        backend.action_sync_products()
        return self._notify(_("Ürün Senkron"), _("Ürünler senkronize edildi."))

    def action_sync_invoices(self):
        backend = self._ensure_backend()
        backend.action_sync_invoices()
        return self._notify(_("Fatura Senkron"), _("Faturalar senkronize edildi."))

    def action_sync_payments(self):
        backend = self._ensure_backend()
        backend.action_sync_payments()
        return self._notify(_("Ödeme Senkron"), _("Ödemeler senkronize edildi."))

    def action_sync_all(self):
        backend = self._ensure_backend()
        backend.action_sync_all()
        return self._notify(
            _("Tüm Senkron"),
            _(
                "Kategoriler, cariler, ürünler, faturalar ve ödemeler senkronize edildi."
            ),
        )
