# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BizimHesapSyncWizard(models.TransientModel):
    """
    BizimHesap Manuel Senkronizasyon Wizard
    """

    _name = "bizimhesap.sync.wizard"
    _description = "BizimHesap Sync Wizard"

    backend_id = fields.Many2one(
        "bizimhesap.backend",
        string="BizimHesap Bağlantısı",
        required=True,
        domain="[('state', '=', 'connected')]",
    )

    sync_type = fields.Selection(
        [
            ("all", "Tümünü Senkronize Et"),
            ("partners", "Sadece Cariler"),
            ("products", "Sadece Ürünler"),
            ("invoices", "Sadece Faturalar"),
            ("payments", "Sadece Ödemeler"),
        ],
        string="Senkronizasyon Tipi",
        default="all",
        required=True,
    )

    direction = fields.Selection(
        [
            ("import", "İçe Aktar (BizimHesap → Odoo)"),
            ("export", "Dışa Aktar (Odoo → BizimHesap)"),
        ],
        string="Yön",
        default="import",
        required=True,
    )

    date_from = fields.Date(
        string="Başlangıç Tarihi",
        help="Fatura senkronizasyonu için",
    )
    date_to = fields.Date(
        string="Bitiş Tarihi",
        help="Fatura senkronizasyonu için",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # Varsayılan backend
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

    def action_sync(self):
        """Senkronizasyonu başlat"""
        self.ensure_one()

        if not self.backend_id:
            raise UserError(_("Lütfen bir BizimHesap bağlantısı seçin!"))

        results = {}

        if self.direction == "import":
            # İçe Aktar
            if self.sync_type in ("all", "partners"):
                results["partners"] = self.backend_id.action_sync_partners()

            if self.sync_type in ("all", "products"):
                results["products"] = self.backend_id.action_sync_products()

            if self.sync_type in ("all", "invoices"):
                results["invoices"] = self.backend_id.action_sync_invoices()

            if self.sync_type in ("all", "payments"):
                results["payments"] = self.backend_id.action_sync_payments()

        else:
            # Dışa Aktar
            if self.sync_type in ("all", "partners"):
                results["partners"] = self._export_partners()

            if self.sync_type in ("all", "products"):
                results["products"] = self._export_products()

        # Sonuç mesajı
        message_parts = []
        for key, value in results.items():
            if isinstance(value, dict):
                message_parts.append(
                    f"{key.title()}: {value.get('created', 0)} oluşturuldu, "
                    f"{value.get('updated', 0)} güncellendi"
                )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Senkronizasyon Tamamlandı"),
                "message": "\n".join(message_parts) or _("İşlem tamamlandı"),
                "type": "success",
                "sticky": True,
            },
        }

    def _export_partners(self):
        """Tüm partner'ları export et"""
        partners = self.env["res.partner"].search(
            [
                ("customer_rank", ">", 0),  # Sadece müşteriler
            ]
        )

        created = updated = failed = 0

        for partner in partners:
            try:
                binding = self.env["bizimhesap.partner.binding"].search(
                    [
                        ("backend_id", "=", self.backend_id.id),
                        ("odoo_id", "=", partner.id),
                    ],
                    limit=1,
                )

                self.backend_id.export_partner(partner)

                if binding:
                    updated += 1
                else:
                    created += 1

            except Exception:
                failed += 1

        return {"created": created, "updated": updated, "failed": failed}

    def _export_products(self):
        """Tüm ürünleri export et"""
        products = self.env["product.product"].search(
            [
                ("sale_ok", "=", True),
            ]
        )

        created = updated = failed = 0

        for product in products:
            try:
                binding = self.env["bizimhesap.product.binding"].search(
                    [
                        ("backend_id", "=", self.backend_id.id),
                        ("odoo_id", "=", product.id),
                    ],
                    limit=1,
                )

                self.backend_id.export_product(product)

                if binding:
                    updated += 1
                else:
                    created += 1

            except Exception:
                failed += 1

        return {"created": created, "updated": updated, "failed": failed}
