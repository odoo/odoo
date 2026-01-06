# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

# Senkronizasyon protokolleri
try:
    from .sync_protocols import SyncProtocols

    SYNC_PROTOCOLS = SyncProtocols()
except ImportError:
    SYNC_PROTOCOLS = None

_logger = logging.getLogger(__name__)

# BizimHesap API Base URL - Doğru URL
BIZIMHESAP_API_BASE = "https://bizimhesap.com/api/b2b"


class BizimHesapBackend(models.Model):
    """
    BizimHesap Bağlantı Ayarları
    """

    _name = "bizimhesap.backend"
    _description = "BizimHesap Backend"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(
        string="Bağlantı Adı",
        required=True,
        tracking=True,
        default="BizimHesap",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Şirket",
        required=True,
        default=lambda self: self.env.company,
    )

    # ═══════════════════════════════════════════════════════════════
    # API AYARLARI
    # ═══════════════════════════════════════════════════════════════

    api_url = fields.Char(
        string="API URL",
        default=BIZIMHESAP_API_BASE,
        required=True,
    )

    # Authentication - BizimHesap B2B API sadece API Key kullanıyor
    api_key = fields.Char(
        string="API Key (Firm ID)",
        required=True,
        help="BizimHesap tarafından sağlanan Firm ID / API Key",
    )

    username = fields.Char(
        string="Kullanıcı Adı",
        help="BizimHesap giriş e-posta adresi (opsiyonel)",
    )

    password = fields.Char(
        string="Şifre",
        help="BizimHesap giriş şifresi (opsiyonel)",
    )

    # Token - B2B API token gerektirmiyor
    access_token = fields.Text(
        string="Access Token",
        readonly=True,
    )
    token_expiry = fields.Datetime(
        string="Token Geçerlilik",
        readonly=True,
    )

    # ═══════════════════════════════════════════════════════════════
    # BAĞLANTI DURUMU
    # ═══════════════════════════════════════════════════════════════

    state = fields.Selection(
        [
            ("draft", "Taslak"),
            ("connected", "Bağlı"),
            ("error", "Hata"),
        ],
        string="Durum",
        default="draft",
        tracking=True,
    )

    last_test_date = fields.Datetime(
        string="Son Test Tarihi",
        readonly=True,
    )

    # ═══════════════════════════════════════════════════════════════
    # SENKRONIZASYON AYARLARI
    # ═══════════════════════════════════════════════════════════════

    sync_partner = fields.Boolean(
        string="Cari Senkronizasyonu",
        default=True,
        help="Müşteri ve tedarikçi senkronizasyonu",
    )
    sync_product = fields.Boolean(
        string="Ürün Senkronizasyonu",
        default=True,
    )
    sync_invoice = fields.Boolean(
        string="Fatura Senkronizasyonu",
        default=True,
    )
    sync_payment = fields.Boolean(
        string="Ödeme Senkronizasyonu",
        default=True,
    )

    # Ödeme mutabakatı ayarları
    auto_reconcile_payments = fields.Boolean(
        string="Otomatik Ödeme Mutabakatı",
        default=True,
        help="İçe aktarılan ödemeleri ilgili faturalarla otomatik olarak eşleştirip mutabakat yapar.",
    )
    payment_reconcile_tolerance = fields.Float(
        string="Mutabakat Toleransı",
        default=0.0,
        help="Ödeme tutarı ile faturanın kalan tutarı arasındaki kabul edilen fark (aynı para birimi için).",
    )

    # Senkronizasyon yönü
    sync_direction = fields.Selection(
        [
            ("import", "İçe Aktar (BizimHesap → Odoo: Cariler, Ürünler)"),
            ("export", "Dışa Aktar (Odoo → BizimHesap: Faturalar)"),
            ("both", "Çift Yönlü (Cariler/Ürünler ← | Faturalar →)"),
        ],
        string="Senkronizasyon Yönü",
        default="both",
        help="BizimHesap B2B API: Cariler/Ürünler çekilir, Faturalar gönderilir",
    )

    # Zamanlama
    auto_sync = fields.Boolean(
        string="Otomatik Senkronizasyon",
        default=True,
    )
    sync_interval = fields.Integer(
        string="Senkronizasyon Aralığı (dakika)",
        default=30,
    )

    # Son senkronizasyon tarihleri
    last_sync_date = fields.Datetime(
        string="Son Senkronizasyon",
        readonly=True,
    )
    last_partner_sync = fields.Datetime(
        string="Son Cari Sync",
        readonly=True,
    )
    last_product_sync = fields.Datetime(
        string="Son Ürün Sync",
        readonly=True,
    )
    last_invoice_sync = fields.Datetime(
        string="Son Fatura Sync",
        readonly=True,
    )
    last_payment_sync = fields.Datetime(
        string="Son Ödeme Sync",
        readonly=True,
    )

    # ═══════════════════════════════════════════════════════════════
    # VARSAYILAN DEĞERLER
    # ═══════════════════════════════════════════════════════════════

    default_customer_account_id = fields.Many2one(
        "account.account",
        string="Varsayılan Müşteri Hesabı",
        domain="[('account_type', '=', 'asset_receivable')]",
    )
    default_supplier_account_id = fields.Many2one(
        "account.account",
        string="Varsayılan Tedarikçi Hesabı",
        domain="[('account_type', '=', 'liability_payable')]",
    )
    default_income_account_id = fields.Many2one(
        "account.account",
        string="Varsayılan Gelir Hesabı",
        domain="[('account_type', '=', 'income')]",
    )
    default_expense_account_id = fields.Many2one(
        "account.account",
        string="Varsayılan Gider Hesabı",
        domain="[('account_type', '=', 'expense')]",
    )

    # ═══════════════════════════════════════════════════════════════
    # LOG İLİŞKİSİ
    # ═══════════════════════════════════════════════════════════════

    sync_log_ids = fields.One2many(
        "bizimhesap.sync.log",
        "backend_id",
        string="Senkronizasyon Logları",
    )

    sync_log_count = fields.Integer(
        compute="_compute_sync_log_count",
        string="Log Sayısı",
    )

    # Binding sayıları
    partner_binding_count = fields.Integer(
        compute="_compute_binding_counts",
        string="Eşleşen Cari",
    )
    product_binding_count = fields.Integer(
        compute="_compute_binding_counts",
        string="Eşleşen Ürün",
    )
    invoice_binding_count = fields.Integer(
        compute="_compute_binding_counts",
        string="Eşleşen Fatura",
    )

    # ═══════════════════════════════════════════════════════════════
    # COMPUTE METHODS
    # ═══════════════════════════════════════════════════════════════

    def _compute_sync_log_count(self):
        for record in self:
            record.sync_log_count = self.env["bizimhesap.sync.log"].search_count(
                [("backend_id", "=", record.id)]
            )

    def _compute_binding_counts(self):
        for record in self:
            record.partner_binding_count = self.env[
                "bizimhesap.partner.binding"
            ].search_count([("backend_id", "=", record.id)])
            record.product_binding_count = self.env[
                "bizimhesap.product.binding"
            ].search_count([("backend_id", "=", record.id)])
            record.invoice_binding_count = self.env[
                "bizimhesap.invoice.binding"
            ].search_count([("backend_id", "=", record.id)])

    # ═══════════════════════════════════════════════════════════════
    # API METHODS
    # ═══════════════════════════════════════════════════════════════

    def _get_headers(self):
        """
        BizimHesap B2B API headers oluştur

        BizimHesap B2B API, hem 'Key' hem 'Token' header'ı olarak
        aynı API Key değerini kullanıyor.
        """
        self.ensure_one()

        return {
            "Key": self.api_key,
            "Token": self.api_key,  # BizimHesap B2B API: Key ve Token aynı değer
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _api_request(self, method, endpoint, data=None, params=None):
        """
        BizimHesap API isteği yap

        :param method: HTTP method (GET, POST, PUT, DELETE)
        :param endpoint: API endpoint (/api/contacts vs.)
        :param data: Request body (dict)
        :param params: Query parameters (dict)
        :return: Response data (dict)
        """
        self.ensure_one()

        url = f"{self.api_url}{endpoint}"
        headers = self._get_headers()

        try:
            _logger.info(f"BizimHesap API Request: {method} {url}")

            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=60,
            )

            # Log the request
            self._create_log(
                operation=f"{method} {endpoint}",
                status="success" if response.ok else "error",
                request_data=json.dumps(data) if data else None,
                response_data=response.text[:5000] if response.text else None,
                status_code=response.status_code,
            )

            response.raise_for_status()

            if response.content:
                return response.json()
            return {}

        except requests.exceptions.RequestException as e:
            _logger.error(f"BizimHesap API error: {e}")
            self._create_log(
                operation=f"{method} {endpoint}",
                status="error",
                error_message=str(e),
            )
            raise UserError(_(f"API Hatası: {e}"))

    def _create_log(self, operation, status, **kwargs):
        """Sync log oluştur"""
        self.env["bizimhesap.sync.log"].sudo().create(
            {
                "backend_id": self.id,
                "operation": operation,
                "status": status,
                **kwargs,
            }
        )

    # ═══════════════════════════════════════════════════════════════
    # B2B API ENDPOINT METHODS
    # ═══════════════════════════════════════════════════════════════

    # Warehouses (Depolar)
    def get_warehouses(self):
        """Tüm depoları getir - B2B API"""
        return self._api_request("GET", "/warehouses")

    # Products (Ürünler)
    def get_products(self):
        """Tüm ürünleri getir - B2B API"""
        return self._api_request("GET", "/products")

    # Categories (Kategoriler)
    def get_categories(self):
        """Tüm kategorileri getir - B2B API"""
        return self._api_request("GET", "/categories")

    # Customers (Müşteriler)
    def get_customers(self):
        """Tüm müşterileri getir - B2B API"""
        return self._api_request("GET", "/customers")

    # Suppliers (Tedarikçiler)
    def get_suppliers(self):
        """Tüm tedarikçileri getir - B2B API"""
        return self._api_request("GET", "/suppliers")

    # Inventory (Stok)
    def get_inventory(self, warehouse_id):
        """Belirli depodaki stok miktarlarını getir - B2B API"""
        return self._api_request("GET", f"/inventory/{warehouse_id}")

    # Abstract (Cari Ekstre)
    def get_customer_abstract(self, customer_id):
        """
        Cari hesap eksترesini getir - B2B API

        :param customer_id: Müşterinin BizimHesap ID'si (external_id)
        :return: Cari hesap harekatleri ve bakiye bilgisi
        """
        return self._api_request("GET", f"/abstract/{customer_id}")

    # Cari ekstre import (otomatik kayıt)
    def action_sync_customer_abstracts(self):
        """
        Tüm bağlı cariler için /abstract verisini çekip Odoo muhasebe kayıtlarına işler.

        Kurallar (varsayılan):
        - type içeriğinde 'tahsilat' veya 'payment' geçiyorsa: tahsilat/ödeme → account.payment
        - type içinde 'satis'/'satış' geçiyorsa: müşteri satış kaydı → account.move (entry) partner alacaklandırılır
        - type içinde 'alis'/'alış' geçiyorsa: tedarikçi alış kaydı → account.move (entry) partner borçlandırılır
        - type içinde 'iptal' geçiyorsa: ters kayıt (işaret ters çevrilir)

        Not: API şeması belirsiz olduğundan, hareket tipi `type` alanı string eşleşmesiyle yorumlanır. Aynı referansın tekrar kaydedilmemesi için `ref` kontrolü yapılır.
        """
        self.ensure_one()

        misc_journal = self._get_misc_journal()
        contra_account = self._get_contra_account(misc_journal)

        bindings = self.env["bizimhesap.partner.binding"].search(
            [("backend_id", "=", self.id)]
        )

        created = skipped = failed = 0

        for binding in bindings:
            partner = binding.odoo_id
            try:
                result = self.get_customer_abstract(binding.external_id)
                if not result or "error" in result:
                    _logger.warning(
                        "Abstract skipped for %s: %s", partner.display_name, result
                    )
                    skipped += 1
                    continue

                self._process_abstract_transactions(
                    partner, binding, result, misc_journal, contra_account
                )
                created += 1
            except Exception as e:
                failed += 1
                _logger.error("Abstract import error for %s: %s", partner.name, e)

        self._create_log(
            operation="Sync Abstracts",
            status="success" if failed == 0 else "warning",
            records_created=created,
            records_failed=failed,
            message=f"İşlenen cari: {created}, Atlanan: {skipped}, Hata: {failed}",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Cari Ekstre Senkronu"),
                "message": _(
                    f"İşlenen cari: {created}, Atlanan: {skipped}, Hata: {failed}"
                ),
                "type": "success" if failed == 0 else "warning",
                "sticky": False,
            },
        }

    def _process_abstract_transactions(
        self, partner, binding, result, misc_journal, contra_account
    ):
        """Abstract içindeki hareketleri muhasebe kayıtlarına işler."""

        data_block = result.get("data") if isinstance(result, dict) else result
        data_block = data_block or {}

        txns = data_block.get("transactions") or data_block.get("abstract") or []

        currency_raw = data_block.get("currency") or data_block.get("balance") or "TRY"
        if isinstance(currency_raw, str) and " " in currency_raw:
            # Örn: "0,00 TL" → TL
            currency_code = currency_raw.split()[-1].upper()
        else:
            currency_code = str(currency_raw).upper() if currency_raw else "TRY"
        if currency_code == "TL":
            currency_code = "TRY"
        currency = self.env["res.currency"].search(
            [("name", "=", currency_code)], limit=1
        )

        def _parse_date(val):
            """Handle multiple incoming date formats (dd.mm.yyyy, dd/mm/yyyy, iso)."""
            if not val:
                return fields.Date.today()

            if isinstance(val, datetime):
                return val.date()

            # Already a date instance
            try:
                if (
                    hasattr(val, "year")
                    and hasattr(val, "month")
                    and hasattr(val, "day")
                ):
                    return fields.Date.to_date(val)
            except Exception:
                pass

            s = str(val).strip()
            if not s:
                return fields.Date.today()

            # Normalize common separators
            normalized = s.replace("/", "-")

            for fmt in [
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%d.%m.%Y",
            ]:
                try:
                    return datetime.strptime(normalized, fmt).date()
                except Exception:
                    continue

            # Fallback to Odoo parser
            try:
                return fields.Date.to_date(s)
            except Exception:
                return fields.Date.today()

        for txn in txns:
            ref_token = str(
                txn.get("id")
                or txn.get("guid")
                or f"{binding.external_id}-{txn.get('trxdate') or txn.get('date')}-{txn.get('note') or txn.get('description')}"
            )

            existing_move = self.env["account.move"].search(
                [
                    ("ref", "=", ref_token),
                    ("partner_id", "=", partner.id),
                ],
                limit=1,
            )
            # account.payment'ta 'ref' alanı olmayabilir; payment_reference kullan
            pay_domain = [
                ("partner_id", "=", partner.id),
            ]
            if "payment_reference" in self.env["account.payment"]._fields:
                pay_domain.append(("payment_reference", "=", ref_token))
            existing_pay = self.env["account.payment"].search(pay_domain, limit=1)

            if existing_move or (
                "payment_reference" in self.env["account.payment"]._fields
                and existing_pay
            ):
                continue

            def _parse_amount(val):
                if val in (None, "", False):
                    return 0.0
                if isinstance(val, (int, float)):
                    return float(val)
                s = str(val)
                s = s.replace(".", "").replace(",", ".")  # 1.234,56 → 1234.56
                try:
                    return float(s)
                except Exception:
                    return 0.0

            debit = _parse_amount(txn.get("debit"))
            credit = _parse_amount(txn.get("credit"))
            amount = _parse_amount(txn.get("amount"))
            if not amount:
                amount = debit or credit
            if amount <= 0:
                continue

            t = (
                txn.get("type") or txn.get("note") or txn.get("description") or ""
            ).lower()
            is_payment = any(
                x in t for x in ["tahsil", "tahsilat", "odeme", "ödeme", "payment"]
            )
            is_sale = any(x in t for x in ["satis", "satış", "sale"])
            is_purchase = any(x in t for x in ["alis", "alış", "purchase"])
            is_cancel = "iptal" in t or "cancel" in t

            move_date = _parse_date(txn.get("date") or txn.get("trxdate"))

            if is_payment:
                self._create_payment_from_abstract(
                    partner, amount, move_date, ref_token, currency, t
                )
                continue

            if is_cancel:
                amount = -amount

            direction = "sale" if is_sale else "purchase" if is_purchase else "entry"
            self._create_move_from_abstract(
                partner,
                amount,
                move_date,
                ref_token,
                currency,
                direction,
                misc_journal,
                contra_account,
                debit_value=debit,
                credit_value=credit,
                raw_type=t,
                description=txn.get("note") or txn.get("description"),
            )

    def _create_payment_from_abstract(
        self, partner, amount, date_val, ref_token, currency, raw_type
    ):
        partner_type = "customer" if (partner.customer_rank or 0) > 0 else "supplier"
        payment_type = "inbound" if partner_type == "customer" else "outbound"

        journal = self.env["account.journal"].search(
            [
                ("type", "in", ["bank", "cash"]),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )

        pay_vals = {
            "payment_type": payment_type,
            "partner_type": partner_type,
            "partner_id": partner.id,
            "amount": abs(amount),
            "date": date_val,
            "company_id": self.company_id.id,
        }
        if "payment_reference" in self.env["account.payment"]._fields:
            pay_vals["payment_reference"] = ref_token
        if journal:
            pay_vals["journal_id"] = journal.id
        if currency:
            pay_vals["currency_id"] = currency.id

        payment = self.env["account.payment"].create(pay_vals)
        payment.action_post()

        try:
            if self.auto_reconcile_payments:
                self._auto_reconcile_payment(payment)
        except Exception as rec_e:
            _logger.warning(f"Payment auto-reconcile warning: {rec_e}")

        _logger.info("Abstract payment created: %s (%s)", payment.name, raw_type)

    def _create_move_from_abstract(
        self,
        partner,
        amount,
        date_val,
        ref_token,
        currency,
        direction,
        misc_journal,
        contra_account,
        debit_value=0.0,
        credit_value=0.0,
        raw_type=None,
        description=None,
    ):

        journal = misc_journal
        if not journal:
            journal = self.env["account.journal"].search(
                [
                    ("type", "=", "general"),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
        if not contra_account and journal:
            contra_account = journal.default_account_id

        recv_acct = partner.property_account_receivable_id
        pay_acct = partner.property_account_payable_id

        if not contra_account:
            contra_account = recv_acct or pay_acct

        if direction == "sale":
            partner_account = recv_acct
            partner_debit = 0.0
            partner_credit = abs(amount)
        elif direction == "purchase":
            partner_account = pay_acct or recv_acct
            partner_debit = abs(amount)
            partner_credit = 0.0
        else:
            partner_account = recv_acct or pay_acct
            if debit_value and not credit_value:
                partner_debit = abs(debit_value)
                partner_credit = 0.0
            elif credit_value and not debit_value:
                partner_debit = 0.0
                partner_credit = abs(credit_value)
            else:
                partner_debit = abs(amount)
                partner_credit = 0.0

        if not partner_account or not contra_account:
            _logger.warning("Skip abstract txn due to missing accounts: %s", ref_token)
            return

        lines = [
            (
                0,
                0,
                {
                    "name": description or raw_type or "Abstract",
                    "partner_id": partner.id,
                    "account_id": partner_account.id,
                    "debit": partner_debit,
                    "credit": partner_credit,
                },
            ),
        ]

        contra_debit = partner_credit
        contra_credit = partner_debit

        lines.append(
            (
                0,
                0,
                {
                    "name": description or raw_type or "Abstract",
                    "account_id": contra_account.id,
                    "debit": contra_debit,
                    "credit": contra_credit,
                },
            )
        )

        move_vals = {
            "move_type": "entry",
            "date": date_val,
            "ref": ref_token,
            "journal_id": journal.id if journal else False,
            "company_id": self.company_id.id,
            "line_ids": lines,
        }
        if currency:
            move_vals["currency_id"] = currency.id

        move = self.env["account.move"].create(move_vals)
        move.action_post()
        _logger.info("Abstract move created: %s (%s)", move.name, raw_type)

    def _get_misc_journal(self):
        return self.env["account.journal"].search(
            [
                ("type", "=", "general"),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )

    def _get_contra_account(self, misc_journal=None):
        if misc_journal and misc_journal.default_account_id:
            return misc_journal.default_account_id

        account = self.env["account.account"].search(
            [
                ("company_ids", "in", self.company_id.id),
            ],
            limit=1,
        )
        return account

    # Invoices (Faturalar)
    def create_invoice(self, data):
        """
        Yeni fatura oluştur - B2B API

        InvoiceType:
        - 3: Satış Faturası
        - 5: Alış Faturası
        """
        return self._api_request("POST", "/addinvoice", data=data)

    def cancel_invoice(self, invoice_guid):
        """
        Faturayı iptal et - B2B API

        :param invoice_guid: AddInvoice'dan alınan GUID
        :return: Response data {"error": "", "status": 0}
        """
        data = {"firmId": self.api_key, "guid": invoice_guid}
        return self._api_request("POST", "/cancelinvoice", data=data)

    # ⚠️ UYARI: Aşağıdaki endpoint'ler BizimHesap B2B API'de desteklenmiyor
    # API Documentation'da sadece /addinvoice (POST) mevcut
    # Fatura listesi çekmek için endpoint YOK!

    def get_invoices(self, start_date=None, end_date=None, invoice_type=None):
        """
        ❌ DESTEKLENM IYOR - BizimHesap B2B API'de bu endpoint yok!

        Faturaları getir - B2B API (MEVCUT DEĞİL)

        Not: BizimHesap sadece /addinvoice (POST) sağlıyor.
        Fatura listesi almak için alternatif endpoint yok.
        """
        _logger.warning("get_invoices NOT supported in BizimHesap B2B API")
        raise UserError(
            "BizimHesap B2B API fatura listesi endpoint'i sağlamıyor. "
            "Sadece /addinvoice (POST) ile fatura gönderilebilir."
        )

    def get_invoice(self, invoice_guid):
        """❌ DESTEKLENMIYOR - Endpoint mevcut değil"""
        _logger.warning("get_invoice NOT supported in BizimHesap B2B API")
        raise UserError("Bu endpoint BizimHesap B2B API'de desteklenmiyor.")

    def update_invoice(self, invoice_guid, data):
        """❌ DESTEKLENMIYOR - Endpoint mevcut değil"""
        _logger.warning("update_invoice NOT supported in BizimHesap B2B API")
        raise UserError("Bu endpoint BizimHesap B2B API'de desteklenmiyor.")

    def delete_invoice(self, invoice_guid):
        """❌ DESTEKLENMIYOR - Fatura silme yerine cancel_invoice kullanın"""
        _logger.warning("delete_invoice NOT supported - use cancel_invoice instead")
        return self.cancel_invoice(invoice_guid)

    # Payments (Tahsilat/Ödeme)
    def get_payments(self, start_date=None, end_date=None, contact_id=None):
        """
        ❌ DESTEKLENMIYOR - BizimHesap B2B API'de ödeme listesi endpoint'i yok!

        ❌ DESTEKLENMIYOR - BizimHesap B2B API'de ödeme listesi endpoint'i yok!

        :param start_date: Başlangıç tarihi (datetime)
        :param end_date: Bitiş tarihi (datetime)
        :param contact_id: Cari ID'si
        :return: Response data
        """
        _logger.warning("get_payments NOT supported in BizimHesap B2B API")
        raise UserError(
            "BizimHesap B2B API ödeme listesi endpoint'i sağlamıyor. "
            "Ödeme bilgileri için /abstract/{musteri-id} kullanabilirsiniz."
        )

    def get_payment(self, payment_guid):
        """❌ DESTEKLENMIYOR - Endpoint mevcut değil"""
        _logger.warning("get_payment NOT supported in BizimHesap B2B API")
        raise UserError("Bu endpoint BizimHesap B2B API'de desteklenmiyor.")

    def create_payment(self, data):
        """❌ DESTEKLENMIYOR - Endpoint mevcut değil"""
        _logger.warning("create_payment NOT supported in BizimHesap B2B API")
        raise UserError("Bu endpoint BizimHesap B2B API'de desteklenmiyor.")

    def update_payment(self, payment_guid, data):
        """❌ DESTEKLENMIYOR - Endpoint mevcut değil"""
        _logger.warning("update_payment NOT supported in BizimHesap B2B API")
        raise UserError("Bu endpoint BizimHesap B2B API'de desteklenmiyor.")

    def delete_payment(self, payment_guid):
        """❌ DESTEKLENMIYOR - Endpoint mevcut değil"""
        _logger.warning("delete_payment NOT supported in BizimHesap B2B API")
        raise UserError("Bu endpoint BizimHesap B2B API'de desteklenmiyor.")

    # Stock Movements (Stok Hareketleri)
    def get_stock_movements(self, warehouse_id=None, start_date=None, end_date=None):
        """
        Stok hareketlerini getir - B2B API

        :param warehouse_id: Depo ID'si
        :param start_date: Başlangıç tarihi (datetime)
        :param end_date: Bitiş tarihi (datetime)
        :return: Response data
        """
        params = {}
        if warehouse_id:
            params["warehouseId"] = warehouse_id
        if start_date:
            params["startDate"] = start_date.isoformat()
        if end_date:
            params["endDate"] = end_date.isoformat()

        return self._api_request("GET", "/stockmovements", params=params)

    # ═══════════════════════════════════════════════════════════════
    # LEGACY API ENDPOINT METHODS (Uyumluluk için)
    # ═══════════════════════════════════════════════════════════════

    def get_contacts(self, page=1, page_size=100):
        """Tüm carileri getir - Müşteri ve tedarikçileri birleştir"""
        # Müşteri ve tedarikçileri birleştirerek döndür
        result = {"data": []}
        try:
            customers_response = self.get_customers()
            if customers_response.get("resultCode") == 1:
                customers = customers_response.get("data", {}).get("customers", [])
                for c in customers:
                    c["contactType"] = 1  # Müşteri
                result["data"].extend(customers)

            suppliers_response = self.get_suppliers()
            if suppliers_response.get("resultCode") == 1:
                suppliers = suppliers_response.get("data", {}).get("suppliers", [])
                for s in suppliers:
                    s["contactType"] = 2  # Tedarikçi
                result["data"].extend(suppliers)
        except Exception as e:
            _logger.error(f"get_contacts error: {e}")
        return result

    def get_contact(self, contact_id):
        """Tek cari getir - B2B API'de desteklenmiyor"""
        _logger.warning("get_contact is not supported in B2B API")
        return {}

    def create_contact(self, data):
        """Yeni cari oluştur - Bu B2B API'de desteklenmiyor"""
        _logger.warning("create_contact is not supported in B2B API")
        return {}

    def update_contact(self, contact_id, data):
        """Cari güncelle - Bu B2B API'de desteklenmiyor"""
        _logger.warning("update_contact is not supported in B2B API")
        return {}

    # Products - Legacy methods
    def get_product(self, product_id):
        """Tek ürün getir - B2B API'de yok"""
        _logger.warning(
            "get_product is not supported in B2B API, use get_products instead"
        )
        return {}

    def create_product(self, data):
        """Yeni ürün oluştur - Bu B2B API'de desteklenmiyor"""
        _logger.warning("create_product is not supported in B2B API")
        return {}

    def update_product(self, product_id, data):
        """Ürün güncelle - Bu B2B API'de desteklenmiyor"""
        _logger.warning("update_product is not supported in B2B API")
        return {}

    # ═══════════════════════════════════════════════════════════════
    # ACTION METHODS
    # ═══════════════════════════════════════════════════════════════

    def action_test_connection(self):
        """
        Bağlantıyı test et - B2B API warehouses endpoint ile

        BizimHesap B2B API: Key ve Token header'ları aynı API Key değerini kullanır
        """
        self.ensure_one()
        try:
            # B2B API'ye basit bir istek at - warehouses listesi al
            url = f"{self.api_url}/warehouses"
            headers = self._get_headers()

            _logger.info(f"Testing BizimHesap connection: {url}")
            _logger.info("Using headers: Key and Token with API Key")

            response = requests.get(url, headers=headers, timeout=30)

            _logger.info(f"BizimHesap test response: {response.status_code}")
            _logger.debug(
                f"Response: {response.text[:500] if response.text else 'No response'}"
            )

            if response.ok:
                result = response.json()

                # Başarılı mı kontrol et (resultCode == 1)
                if result.get("resultCode") == 1:
                    warehouses = result.get("data", {}).get("warehouses", [])
                    warehouse_count = len(warehouses)

                    self.write(
                        {
                            "state": "connected",
                            "last_test_date": fields.Datetime.now(),
                        }
                    )

                    # Log başarılı bağlantı
                    self._create_log(
                        operation="Test Connection",
                        status="success",
                        message=f"Bağlantı başarılı. {warehouse_count} depo bulundu.",
                        response_data=response.text[:1000] if response.text else None,
                        status_code=response.status_code,
                    )

                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": _("Başarılı"),
                            "message": _(
                                f"BizimHesap bağlantısı başarılı! {warehouse_count} depo bulundu."
                            ),
                            "type": "success",
                            "sticky": False,
                        },
                    }
                else:
                    error_text = result.get("errorText", "Bilinmeyen hata")
                    self.write({"state": "error"})
                    self._create_log(
                        operation="Test Connection",
                        status="error",
                        message=f"API Hatası: {error_text}",
                        response_data=response.text[:1000] if response.text else None,
                        status_code=response.status_code,
                    )
                    raise UserError(_(f"API Hatası: {error_text}"))
            else:
                self.write({"state": "error"})
                self._create_log(
                    operation="Test Connection",
                    status="error",
                    message=f"Bağlantı hatası. Status: {response.status_code}",
                    response_data=response.text[:1000] if response.text else None,
                    status_code=response.status_code,
                )
                raise UserError(_(f"Bağlantı hatası: HTTP {response.status_code}"))

        except requests.exceptions.RequestException as e:
            self.write({"state": "error"})
            self._create_log(
                operation="Test Connection",
                status="error",
                error_message=str(e),
            )
            raise UserError(_(f"Bağlantı hatası: {e}"))

    def action_sync_all(self):
        """Tüm verileri senkronize et"""
        self.ensure_one()

        total_created = total_updated = total_failed = 0

        # 1. Önce kategorileri senkronize et
        try:
            result = self.action_sync_categories()
            _logger.info("Categories sync completed")
        except Exception as e:
            _logger.error(f"Category sync error: {e}")

        # 2. Carileri senkronize et (Müşteri + Tedarikçi)
        if self.sync_partner:
            try:
                self.action_sync_partners()
            except Exception as e:
                _logger.error(f"Partner sync error: {e}")

        # 3. Ürünleri senkronize et
        if self.sync_product:
            try:
                self.action_sync_products()
            except Exception as e:
                _logger.error(f"Product sync error: {e}")

        # 4. Faturalar senkronize et
        if self.sync_invoice:
            try:
                self.action_sync_invoices()
            except Exception as e:
                _logger.error(f"Invoice sync error: {e}")

        # 5. Ödeme kayıtlarını senkronize et
        if self.sync_payment:
            try:
                self.action_sync_payments()
            except Exception as e:
                _logger.error(f"Payment sync error: {e}")

        self.last_sync_date = fields.Datetime.now()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Senkronizasyon Tamamlandı"),
                "message": _(
                    "Tüm veriler (kategoriler, cariler, ürünler, faturalar, ödemeler) senkronize edildi."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_sync_categories(self):
        """Kategorileri senkronize et - B2B API"""
        self.ensure_one()
        _logger.info(f"Starting category sync for {self.name}")

        created = updated = 0

        try:
            response = self.get_categories()
            if response.get("resultCode") == 1:
                categories = response.get("data", {}).get("categories", [])
                _logger.info(f"Found {len(categories)} categories from BizimHesap")

                for cat_data in categories:
                    cat_name = cat_data.get("title") or cat_data.get(
                        "name", "Bilinmiyor"
                    )

                    # Mevcut kategori ara
                    existing = self.env["product.category"].search(
                        [("name", "=", cat_name)], limit=1
                    )

                    if not existing:
                        self.env["product.category"].create(
                            {
                                "name": cat_name,
                            }
                        )
                        created += 1
                    else:
                        updated += 1

        except Exception as e:
            _logger.error(f"Category sync error: {e}")

        self._create_log(
            operation="Sync Categories",
            status="success",
            records_created=created,
            records_updated=updated,
            message=f"Oluşturulan: {created}, Mevcut: {updated}",
        )

        return {"created": created, "updated": updated}

    def action_sync_warehouses(self):
        """Depoları senkronize et - B2B API"""
        self.ensure_one()
        _logger.info(f"Starting warehouse sync for {self.name}")

        created = updated = 0

        try:
            response = self.get_warehouses()
            if response.get("resultCode") == 1:
                warehouses = response.get("data", {}).get("warehouses", [])
                _logger.info(f"Found {len(warehouses)} warehouses from BizimHesap")

                for wh_data in warehouses:
                    wh_name = wh_data.get("title", "Bilinmiyor")
                    external_id = wh_data.get("id")

                    # Mevcut depo ara
                    existing = self.env["stock.warehouse"].search(
                        [("name", "=", wh_name)], limit=1
                    )

                    if not existing:
                        # Kısa kod oluştur (ilk 5 karakter)
                        code = wh_name[:5].upper().replace(" ", "")
                        self.env["stock.warehouse"].create(
                            {
                                "name": wh_name,
                                "code": code,
                                "company_id": self.company_id.id,
                            }
                        )
                        created += 1
                    else:
                        updated += 1

        except Exception as e:
            _logger.error(f"Warehouse sync error: {e}")

        self._create_log(
            operation="Sync Warehouses",
            status="success",
            records_created=created,
            records_updated=updated,
            message=f"Oluşturulan: {created}, Mevcut: {updated}",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Depo Senkronizasyonu"),
                "message": _(f"Oluşturulan: {created}, Mevcut: {updated}"),
                "type": "success",
                "sticky": False,
            },
        }

    def action_sync_partners(self):
        """
        Müşteri ve Tedarikçileri senkronize et - B2B API

        /customers ve /suppliers endpoint'lerinden veri çeker
        """
        self.ensure_one()
        _logger.info(f"Starting partner sync for {self.name}")

        created = updated = failed = 0

        # Müşterileri senkronize et
        try:
            response = self.get_customers()
            if response.get("resultCode") == 1:
                customers = response.get("data", {}).get("customers", [])
                _logger.info(f"Found {len(customers)} customers from BizimHesap")

                for customer_data in customers:
                    customer_data["contactType"] = 1  # Müşteri
                    try:
                        result = self._import_partner(customer_data)
                        if result == "created":
                            created += 1
                        elif result == "updated":
                            updated += 1
                    except Exception as e:
                        failed += 1
                        _logger.error(f"Customer import error: {e}")
        except Exception as e:
            _logger.error(f"Customer sync error: {e}")

        # Tedarikçileri senkronize et
        try:
            response = self.get_suppliers()
            if response.get("resultCode") == 1:
                suppliers = response.get("data", {}).get("suppliers", [])
                _logger.info(f"Found {len(suppliers)} suppliers from BizimHesap")

                for supplier_data in suppliers:
                    supplier_data["contactType"] = 2  # Tedarikçi
                    try:
                        result = self._import_partner(supplier_data)
                        if result == "created":
                            created += 1
                        elif result == "updated":
                            updated += 1
                    except Exception as e:
                        failed += 1
                        _logger.error(f"Supplier import error: {e}")
        except Exception as e:
            _logger.error(f"Supplier sync error: {e}")

        self.last_partner_sync = fields.Datetime.now()

        self._create_log(
            operation="Sync Partners",
            status="success" if failed == 0 else "warning",
            records_created=created,
            records_updated=updated,
            records_failed=failed,
            message=f"Oluşturulan: {created}, Güncellenen: {updated}, Hatalı: {failed}",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Cari Senkronizasyonu"),
                "message": _(
                    f"Oluşturulan: {created}, Güncellenen: {updated}, Hatalı: {failed}"
                ),
                "type": "success" if failed == 0 else "warning",
                "sticky": False,
            },
        }

    def _import_partner(self, data):
        """
        Tek cari import et - Protokollerle eşleştirme

        Eşleştirme sırası:
        1. VKN/TCKN (vergi numarası) → Kesin eşleşme
        2. Telefon → Kesin eşleşme
        3. E-posta → Kesin eşleşme
        4. İsim benzerliği ≥%80 + farklı adres → Şube olarak ekle
        5. İsim benzerliği ≥%50 → Güncelle
        6. Hiçbiri → Yeni oluştur
        """
        external_id = str(data.get("id"))

        # Mevcut binding kontrol
        binding = self.env["bizimhesap.partner.binding"].search(
            [
                ("backend_id", "=", self.id),
                ("external_id", "=", external_id),
            ],
            limit=1,
        )

        # Odoo değerlerine dönüştür
        partner_vals = self._map_partner_to_odoo(data)

        if binding:
            # Mevcut kayıt - güncelle
            binding.odoo_id.write(partner_vals)
            binding.write(
                {
                    "sync_date": fields.Datetime.now(),
                    "external_data": json.dumps(data),
                }
            )
            return "updated"

        # Protokollerle eşleştirme
        source_partner = {
            "name": data.get("title", ""),
            "vat": data.get("taxno") or data.get("taxNumber"),
            "phone": data.get("phone"),
            "email": data.get("email"),
            "street": data.get("address"),
            "city": "",  # BizimHesap'da ayrı alan yok
        }

        # Tüm mevcut partnerları al
        all_partners = self.env["res.partner"].search_read(
            [("active", "=", True)],
            [
                "id",
                "name",
                "vat",
                "phone",
                "mobile",
                "email",
                "street",
                "city",
                "parent_id",
            ],
        )

        # Protokol ile eşleştir
        match = {"match_type": "new"}
        if SYNC_PROTOCOLS:
            match = SYNC_PROTOCOLS.match_partner(source_partner, all_partners)

        if match["match_type"] == "exact":
            # Kesin eşleşme - VKN/Telefon/E-posta ile bulundu
            partner_id = match["matched_partner"]["id"]
            partner = self.env["res.partner"].browse(partner_id)
            partner.write(partner_vals)

            # Binding oluştur
            self.env["bizimhesap.partner.binding"].create(
                {
                    "backend_id": self.id,
                    "external_id": external_id,
                    "odoo_id": partner.id,
                    "sync_date": fields.Datetime.now(),
                    "external_data": json.dumps(data),
                }
            )
            _logger.info(f"Partner eşleşti ({match['reason']}): {data.get('title')}")
            return "updated"

        elif match["match_type"] == "branch":
            # Şube tespit edildi - aynı isim, farklı adres
            parent_id = match["parent_id"]
            branch_name = match["branch_name"]

            partner_vals["name"] = branch_name
            partner_vals["parent_id"] = parent_id

            partner = self.env["res.partner"].create(partner_vals)

            self.env["bizimhesap.partner.binding"].create(
                {
                    "backend_id": self.id,
                    "external_id": external_id,
                    "odoo_id": partner.id,
                    "sync_date": fields.Datetime.now(),
                    "external_data": json.dumps(data),
                }
            )
            _logger.info(f"Şube oluşturuldu: {branch_name} (Parent: {parent_id})")
            return "created"

        elif match["match_type"] == "similar":
            # Benzer isim - güncelle
            partner_id = match["matched_partner"]["id"]
            partner = self.env["res.partner"].browse(partner_id)
            partner.write(partner_vals)

            self.env["bizimhesap.partner.binding"].create(
                {
                    "backend_id": self.id,
                    "external_id": external_id,
                    "odoo_id": partner.id,
                    "sync_date": fields.Datetime.now(),
                    "external_data": json.dumps(data),
                }
            )
            _logger.info(
                f"Benzer partner güncellendi ({match['reason']}): {data.get('title')}"
            )
            return "updated"

        else:
            # Yeni cari oluştur
            partner = self.env["res.partner"].create(partner_vals)

            self.env["bizimhesap.partner.binding"].create(
                {
                    "backend_id": self.id,
                    "external_id": external_id,
                    "odoo_id": partner.id,
                    "sync_date": fields.Datetime.now(),
                    "external_data": json.dumps(data),
                }
            )
            _logger.info(f"Yeni cari oluşturuldu: {data.get('title')}")
            return "created"

    def _map_partner_to_odoo(self, data):
        """
        BizimHesap cari → Odoo partner dönüşümü

        BizimHesap B2B API Field Mapping:
        - id: External ID
        - code: Cari kodu
        - title: Cari adı
        - address: Adres
        - phone: Telefon
        - taxno: Vergi numarası
        - taxoffice: Vergi dairesi
        - authorized: Yetkili kişi
        - balance: Bakiye
        - chequeandbond: Çek/Senet bakiyesi
        - currency: Para birimi
        - email: E-posta
        """
        contact_type = data.get("contactType", 1)

        vals = {
            "name": data.get("title", "Bilinmiyor"),
            "vat": data.get("taxno")
            or data.get("taxNumber"),  # taxno (B2B) veya taxNumber
            "phone": data.get("phone"),
            "email": data.get("email"),
            "street": data.get("address"),
            "comment": data.get("authorized"),  # Yetkili kişiyi nota ekle
            "ref": data.get("code") if data.get("code") else None,
        }

        # Bakiye bilgileri
        balance_str = data.get("balance", "0,00")
        chequeandbond_str = data.get("chequeandbond", "0,00")

        # Türkçe formatı Python float'a çevir (1.234,56 → 1234.56)
        try:
            balance = float(balance_str.replace(".", "").replace(",", "."))
            vals["bizimhesap_balance"] = balance
        except (ValueError, AttributeError):
            vals["bizimhesap_balance"] = 0.0

        try:
            chequeandbond = float(chequeandbond_str.replace(".", "").replace(",", "."))
            vals["bizimhesap_cheque_bond"] = chequeandbond
        except (ValueError, AttributeError):
            vals["bizimhesap_cheque_bond"] = 0.0

        # Para birimi ve son güncelleme
        vals["bizimhesap_currency"] = data.get("currency", "TL")
        vals["bizimhesap_last_balance_update"] = fields.Datetime.now()

        # None değerleri temizle
        vals = {k: v for k, v in vals.items() if v is not None}

        # Cari tipi: 1=Müşteri, 2=Tedarikçi
        if contact_type == 1:
            vals["customer_rank"] = 1
        elif contact_type == 2:
            vals["supplier_rank"] = 1

        # Vergi dairesi
        tax_office = data.get("taxoffice") or data.get("taxOffice")
        if tax_office:
            # l10n_tr modülü yüklüyse
            if "l10n_tr_tax_office_name" in self.env["res.partner"]._fields:
                vals["l10n_tr_tax_office_name"] = tax_office

        return vals

    def action_sync_products(self):
        """
        Ürünleri senkronize et - B2B API formatı

        B2B API /products endpoint'i tek seferde tüm ürünleri döndürür.
        """
        self.ensure_one()
        _logger.info(f"Starting product sync for {self.name}")

        created = updated = failed = 0

        try:
            response = self.get_products()

            # B2B API response formatı: {"resultCode": 1, "data": {"products": [...]}}
            if response.get("resultCode") == 1:
                products = response.get("data", {}).get("products", [])

                _logger.info(f"Found {len(products)} products from BizimHesap")

                for product_data in products:
                    try:
                        result = self._import_product(product_data)
                        if result == "created":
                            created += 1
                        elif result == "updated":
                            updated += 1
                    except Exception as e:
                        failed += 1
                        _logger.error(f"Product import error: {e}")
            else:
                error_text = response.get("errorText", "Bilinmeyen hata")
                _logger.error(f"BizimHesap API error: {error_text}")
                raise UserError(_(f"API Hatası: {error_text}"))

        except Exception as e:
            _logger.error(f"Product sync error: {e}")
            raise

        self.last_product_sync = fields.Datetime.now()

        self._create_log(
            operation="Sync Products",
            status="success",
            records_created=created,
            records_updated=updated,
            records_failed=failed,
            message=f"Oluşturulan: {created}, Güncellenen: {updated}, Hatalı: {failed}",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Ürün Senkronizasyonu"),
                "message": _(
                    f"Oluşturulan: {created}, Güncellenen: {updated}, Hatalı: {failed}"
                ),
                "type": "success" if failed == 0 else "warning",
                "sticky": False,
            },
        }

    def _import_product(self, data):
        """
        Tek ürün import et - Ürün kodu + Barkod ile eşleştirme

        Eşleştirme sırası:
        1. Ürün kodu + Barkod kombinasyonu → Kesin eşleşme (güncelle)
        2. Ürün kodu aynı + Barkod farklı → Varyant oluştur
        3. Ürün kodu aynı + Barkod boş → Mevcut ürünü güncelle
        4. Hiçbiri → Yeni ürün oluştur
        """
        external_id = str(data.get("id"))
        product_code = data.get("code", "").strip()
        barcode = data.get("barcode", "").strip()

        # Mevcut binding kontrol
        binding = self.env["bizimhesap.product.binding"].search(
            [
                ("backend_id", "=", self.id),
                ("external_id", "=", external_id),
            ],
            limit=1,
        )

        product_vals = self._map_product_to_odoo(data)

        if binding and binding.odoo_id:
            # Mevcut kayıt - güncelle
            binding.odoo_id.write(product_vals)
            binding.write(
                {
                    "sync_date": fields.Datetime.now(),
                    "external_data": json.dumps(data),
                }
            )
            _logger.info(f"Ürün güncellendi (binding): {data.get('title')}")
            return "updated"

        # ═══════════════════════════════════════════════════════════════
        # EŞLEŞTIRME LOGIC: Ürün Kodu + Barkod Kombinasyonu
        # ═══════════════════════════════════════════════════════════════

        # 1. KESIN EŞLEŞME: Ürün kodu + Barkod ikisi de aynı
        if product_code and barcode:
            product = self.env["product.product"].search(
                [
                    ("default_code", "=", product_code),
                    ("barcode", "=", barcode),
                ],
                limit=1,
            )
            if product:
                product.write(product_vals)
                self.env["bizimhesap.product.binding"].create(
                    {
                        "backend_id": self.id,
                        "external_id": external_id,
                        "odoo_id": product.id,
                        "sync_date": fields.Datetime.now(),
                        "external_data": json.dumps(data),
                    }
                )
                _logger.info(
                    f"✅ Ürün eşleşti (kod+barkod): {product_code} / {barcode}"
                )
                return "updated"

        # 2. VARYANT: Ürün kodu aynı, Barkod farklı
        if product_code:
            # Aynı ürün koduna sahip product template'i bul
            template = self.env["product.template"].search(
                [("product_variant_ids.default_code", "=", product_code)],
                limit=1,
            )

            if template:
                # Aynı template altında bu barkoda sahip varyant var mı?
                existing_variant = self.env["product.product"].search(
                    [
                        ("product_tmpl_id", "=", template.id),
                        ("barcode", "=", barcode),
                    ],
                    limit=1,
                )

                if existing_variant:
                    # Var → güncelle
                    existing_variant.write(product_vals)
                    self.env["bizimhesap.product.binding"].create(
                        {
                            "backend_id": self.id,
                            "external_id": external_id,
                            "odoo_id": existing_variant.id,
                            "sync_date": fields.Datetime.now(),
                            "external_data": json.dumps(data),
                        }
                    )
                    _logger.info(f"✅ Varyant güncellendi: {product_code} / {barcode}")
                    return "updated"
                else:
                    # Yok → Mevcut product'ı güncelle (varyant oluşturma yerine)
                    # NOT: Odoo 19'da varyant attribute olmadan yeni variant oluşturmak sorun yaratıyor
                    # Bu yüzden mevcut ürünü güncelliyoruz
                    existing_product = self.env["product.product"].search(
                        [
                            ("product_tmpl_id", "=", template.id),
                        ],
                        limit=1,
                    )

                    if existing_product:
                        # Mevcut ürünü güncelle
                        existing_product.write(product_vals)
                        self.env["bizimhesap.product.binding"].create(
                            {
                                "backend_id": self.id,
                                "external_id": external_id,
                                "odoo_id": existing_product.id,
                                "sync_date": fields.Datetime.now(),
                                "external_data": json.dumps(data),
                            }
                        )
                        _logger.info(
                            f"✅ Ürün güncellendi (variant logic): {product_code} / {barcode}"
                        )
                        return "updated"
                    else:
                        # Template var ama product yok → Yeni oluştur
                        new_product = self.env["product.product"].create(product_vals)
                        self.env["bizimhesap.product.binding"].create(
                            {
                                "backend_id": self.id,
                                "external_id": external_id,
                                "odoo_id": new_product.id,
                                "sync_date": fields.Datetime.now(),
                                "external_data": json.dumps(data),
                            }
                        )
                        _logger.info(
                            f"🆕 Yeni ürün oluşturuldu (variant): {product_code} / {barcode}"
                        )
                        return "created"
            else:
                # Template yok → Aynı ürün koduyla ürün var mı?
                product = self.env["product.product"].search(
                    [("default_code", "=", product_code)],
                    limit=1,
                )
                if product:
                    # Mevcut ürünü güncelle
                    product.write(product_vals)
                    self.env["bizimhesap.product.binding"].create(
                        {
                            "backend_id": self.id,
                            "external_id": external_id,
                            "odoo_id": product.id,
                            "sync_date": fields.Datetime.now(),
                            "external_data": json.dumps(data),
                        }
                    )
                    _logger.info(f"✅ Ürün güncellendi (kod): {product_code}")
                    return "updated"

        # 3. BARKOD İLE EŞLEŞTIRME
        if barcode:
            product = self.env["product.product"].search(
                [("barcode", "=", barcode)],
                limit=1,
            )
            if product:
                product.write(product_vals)
                self.env["bizimhesap.product.binding"].create(
                    {
                        "backend_id": self.id,
                        "external_id": external_id,
                        "odoo_id": product.id,
                        "sync_date": fields.Datetime.now(),
                        "external_data": json.dumps(data),
                    }
                )
                _logger.info(f"✅ Ürün eşleşti (barkod): {barcode}")
                return "updated"

        # 4. YENİ ÜRÜN OLUŞTUR
        product = self.env["product.product"].create(product_vals)
        self.env["bizimhesap.product.binding"].create(
            {
                "backend_id": self.id,
                "external_id": external_id,
                "odoo_id": product.id,
                "sync_date": fields.Datetime.now(),
                "external_data": json.dumps(data),
            }
        )
        _logger.info(f"🆕 Yeni ürün oluşturuldu: {data.get('title')}")
        return "created"

    def _map_product_to_odoo(self, data):
        """
        BizimHesap B2B API ürün → Odoo product dönüşümü

        B2B API Field Mapping:
        - id: External ID
        - isActive: Aktif durum
        - code: Ürün kodu
        - barcode: Barkod
        - title: Ürün adı
        - price: Satış fiyatı (KDV dahil)
        - buyingPrice: Alış fiyatı
        - currency: Para birimi (TL)
        - unit: Birim (Adet)
        - tax: KDV oranı (%)
        - photo: Ürün fotoğrafı JSON
        - description: Açıklama
        - brand: Marka
        - category: Kategori
        - quantity: Stok miktarı
        """
        vals = {
            "name": data.get("title", "Bilinmiyor"),
            "default_code": data.get("code") or "",
            "barcode": data.get("barcode") or False,
            "description_sale": data.get("description")
            or data.get("ecommerceDescription", ""),
            "description_purchase": data.get("note", ""),
            "list_price": float(data.get("price", 0)),
            "standard_price": float(data.get("buyingPrice", 0)),
            "active": data.get("isActive", 1) == 1,
            "type": "consu",  # Stoklanan ürün
            "sale_ok": True,
            "purchase_ok": True,
        }

        # Birim dönüşümü
        unit = data.get("unit", "Adet")
        unit_mapping = {
            "Adet": "Units",
            "Kg": "kg",
            "Lt": "Liters",
            "M": "m",
            "Paket": "Units",
            "Koli": "Units",
        }
        odoo_unit = unit_mapping.get(unit, "Units")
        uom = self.env["uom.uom"].search([("name", "ilike", odoo_unit)], limit=1)
        if uom:
            vals["uom_id"] = uom.id
            # Odoo 19'da uom_po_id product.template'de, product.product'da değil
            # Sadece purchase modülü yüklüyse mevcut
            if "uom_po_id" in self.env["product.product"]._fields:
                vals["uom_po_id"] = uom.id

        # KDV oranı
        tax_rate = float(data.get("tax", 20))
        if tax_rate:
            tax = self.env["account.tax"].search(
                [
                    ("amount", "=", tax_rate),
                    ("type_tax_use", "=", "sale"),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if tax:
                vals["taxes_id"] = [(6, 0, [tax.id])]

        # Marka ve Kategori notlara ekle
        brand = data.get("brand", "")
        category = data.get("category", "")
        if brand or category:
            notes = []
            if brand:
                notes.append(f"Marka: {brand}")
            if category:
                notes.append(f"Kategori: {category}")
            vals["description_purchase"] = "\n".join(notes)

        return vals

    def _send_invoice_to_bizimhesap(self, invoice):
        """
        Tek faturayı BizimHesap'a gönder

        :param invoice: account.move recordu
        :return: {"success": True/False, "guid": ..., "error": ...}
        """
        self.ensure_one()
        _logger.info(f"Sending invoice {invoice.name} to BizimHesap")

        try:
            # Fatura verisini hazırla
            data = self._map_invoice_to_bizimhesap(invoice)

            # API'ye gönder
            response = self._api_request("POST", "/addinvoice", data=data)

            if response.get("error"):
                _logger.error(
                    f"BizimHesap API error for {invoice.name}: {response.get('error')}"
                )
                return {"success": False, "error": response.get("error"), "guid": ""}

            guid = response.get("guid", "")
            if not guid:
                _logger.error(f"No GUID returned for {invoice.name}")
                return {"success": False, "error": "GUID alınamadı", "guid": ""}

            _logger.info(f"Invoice {invoice.name} sent successfully with GUID: {guid}")
            return {
                "success": True,
                "guid": guid,
                "url": response.get("url", ""),
                "error": "",
            }

        except Exception as e:
            _logger.error(f"Exception sending invoice {invoice.name}: {e}")
            return {"success": False, "error": str(e), "guid": ""}

    def action_sync_invoices(self):
        """
        Faturaları senkronize et - BI-DIRECTIONAL

        BizimHesap B2B API:
        - GET /invoices: Desteklenmiyor ❌
        - POST /addinvoice: Faturaları gönder ✓

        Mantık: Odoo'daki unsent faturalar → BizimHesap'e gönder
        """
        self.ensure_one()
        _logger.info(f"Starting invoice sync for {self.name}")

        sent = failed = 0

        try:
            # Odoo'daki son 30 günün faturalarını al - BizimHesap'a henüz gönderilmemiş olanlar
            cutoff_date = datetime.now() - timedelta(days=30)

            invoices = self.env["account.move"].search(
                [
                    ("move_type", "in", ["out_invoice", "in_invoice"]),
                    ("state", "=", "posted"),
                    ("invoice_date", ">=", cutoff_date.date()),
                ]
            )

            for invoice in invoices:
                # BizimHesap binding var mı kontrol et
                binding = self.env["bizimhesap.invoice.binding"].search(
                    [
                        ("backend_id", "=", self.id),
                        ("odoo_id", "=", invoice.id),
                    ],
                    limit=1,
                )

                # Binding varsa ve başarılı ise, geri al (zaten gönderilmiş)
                if binding and binding.sync_state == "synced":
                    continue

                try:
                    # Faturayı BizimHesap'a gönder
                    result = self._send_invoice_to_bizimhesap(invoice)
                    if result.get("success"):
                        sent += 1

                        # Binding oluştur veya güncelle
                        if binding:
                            binding.write(
                                {
                                    "external_id": result.get("guid", ""),
                                    "sync_date": fields.Datetime.now(),
                                    "sync_state": "synced",
                                    "external_data": json.dumps(result),
                                }
                            )
                        else:
                            self.env["bizimhesap.invoice.binding"].create(
                                {
                                    "backend_id": self.id,
                                    "external_id": result.get("guid", ""),
                                    "odoo_id": invoice.id,
                                    "sync_date": fields.Datetime.now(),
                                    "sync_state": "synced",
                                    "external_data": json.dumps(result),
                                }
                            )
                    else:
                        failed += 1
                        error_msg = result.get("error", "Bilinmeyen hata")
                        _logger.error(
                            f"Invoice send error ({invoice.name}): {error_msg}"
                        )

                except Exception as e:
                    failed += 1
                    _logger.error(f"Invoice send error ({invoice.name}): {e}")

        except Exception as e:
            _logger.error(f"Invoice sync error: {e}")

        self.last_invoice_sync = fields.Datetime.now()

        self._create_log(
            operation="Sync Invoices",
            status="success" if failed == 0 else "warning",
            records_created=sent,
            records_failed=failed,
            message=f"Gönderilen: {sent}, Hatalı: {failed}",
        )

        return {"sent": sent, "failed": failed}

    def action_sync_payments(self):
        """
        Ödeme kayıtlarını senkronize et - B2B API

        BizimHesap'taki tahsilat/ödeme kaydalarını Odoo'ya aktarır.
        """
        self.ensure_one()
        _logger.info(f"Starting payment sync for {self.name}")

        created = updated = failed = 0

        # Son 30 günlük ödemeleri çek
        start_date = datetime.now() - timedelta(days=30)

        try:
            response = self.get_payments(start_date=start_date)

            if response.get("resultCode") == 1:
                payments = response.get("data", {}).get("payments", [])
                _logger.info(f"Found {len(payments)} payments from BizimHesap")

                for payment_data in payments:
                    try:
                        result = self._import_payment(payment_data)
                        if result == "created":
                            created += 1
                        elif result == "updated":
                            updated += 1
                    except Exception as e:
                        failed += 1
                        _logger.error(f"Payment import error: {e}")
            else:
                error_text = response.get("errorText", "Bilinmeyen hata")
                _logger.error(f"BizimHesap API error: {error_text}")

        except Exception as e:
            _logger.error(f"Payment sync error: {e}")

        self.last_payment_sync = fields.Datetime.now()

        self._create_log(
            operation="Sync Payments",
            status="success" if failed == 0 else "warning",
            records_created=created,
            records_updated=updated,
            records_failed=failed,
            message=f"Oluşturulan: {created}, Güncellenen: {updated}, Hatalı: {failed}",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Ödeme Senkronizasyonu"),
                "message": _(
                    f"Oluşturulan: {created}, Güncellenen: {updated}, Hatalı: {failed}"
                ),
                "type": "success" if failed == 0 else "warning",
                "sticky": False,
            },
        }

    def _import_payment(self, data):
        """
        Tek ödeme kaydı import et

        BizimHesap payment data'sını Odoo account.payment kaydına dönüştür.
        """
        external_id = str(data.get("guid") or data.get("id"))

        # Mevcut binding kontrol
        binding = self.env.get("bizimhesap.payment.binding")
        if binding:
            existing = binding.search(
                [
                    ("backend_id", "=", self.id),
                    ("external_id", "=", external_id),
                ],
                limit=1,
            )
            if existing:
                # Ödeme zaten var, atla
                return "skipped"

        # Partner bul
        contact_id = data.get("contactId")
        partner = None

        if contact_id:
            partner_binding = self.env["bizimhesap.partner.binding"].search(
                [
                    ("backend_id", "=", self.id),
                    ("external_id", "=", str(contact_id)),
                ],
                limit=1,
            )
            if partner_binding:
                partner = partner_binding.odoo_id

        if not partner:
            _logger.warning(f"Partner not found for payment: {external_id}")
            return "skipped"

        # Ödeme tipini belirle (müşteri/tedarikçi)
        partner_type = "customer" if (partner.customer_rank or 0) > 0 else "supplier"
        payment_type = "inbound" if partner_type == "customer" else "outbound"

        # Journal seçimi (paymentType: 1=Nakit → cash, diğerleri → bank)
        payment_kind = int(data.get("paymentType") or 0)
        journal_type = "cash" if payment_kind == 1 else "bank"
        journal = self.env["account.journal"].search(
            [
                ("type", "=", journal_type),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )
        if not journal:
            # Fallback: herhangi bir bank/cash journal
            journal = self.env["account.journal"].search(
                [("type", "=", journal_type)], limit=1
            )

        # Para birimi
        currency_code = (data.get("currency") or "TL").upper()
        if currency_code == "TL":
            currency_code = "TRY"
        currency = self.env["res.currency"].search(
            [("name", "=", currency_code)], limit=1
        )

        # Tarih
        pay_date = data.get("paymentDate") or fields.Date.today()

        # Ödeme kaydını oluştur
        try:
            payment_vals = {
                "payment_type": payment_type,
                "partner_type": partner_type,
                "partner_id": partner.id,
                "amount": float(data.get("amount", 0.0)),
                "date": pay_date,
                "journal_id": journal.id if journal else False,
                "ref": data.get("description") or external_id,
            }
            if currency:
                payment_vals["currency_id"] = currency.id

            payment = self.env["account.payment"].create(payment_vals)
            # Post et ki hareket oluşturulsun
            payment.action_post()

            # Otomatik mutabakat
            try:
                if self.auto_reconcile_payments:
                    self._auto_reconcile_payment(payment)
            except Exception as rec_e:
                _logger.warning(f"Payment auto-reconcile warning: {rec_e}")

            # İsteğe bağlı: binding modeli varsa kaydet
            if binding:
                binding.create(
                    {
                        "backend_id": self.id,
                        "external_id": external_id,
                        "external_code": data.get("description") or external_id,
                        "contact_type": contact_type,
                        "external_amount": float(data.get("amount", 0.0)),
                        "external_date": pay_date,
                        "external_description": data.get("description", ""),
                        "external_data": json.dumps(data),
                        "sync_date": fields.Datetime.now(),
                    }
                )

            _logger.info(f"Payment created: {payment.name} ({external_id})")
            return "created"

        except Exception as e:
            _logger.error(f"Payment import error: {e}")
            return "failed"

    def _map_payment_to_odoo(self, data, partner):
        """
        BizimHesap ödeme → Odoo veri dönüşümü

        BizimHesap payment fields:
        - guid: Payment GUID
        - description: Açıklama
        - amount: Tutar
        - currency: Para birimi
        - paymentDate: Ödeme tarihi
        - paymentType: Ödeme tipi (1=Nakit, 2=Banka, vb)
        - contactId: Cari ID'si
        """
        vals = {
            "partner_id": partner.id,
            "amount": float(data.get("amount", 0)),
            "payment_date": data.get("paymentDate"),
            "description": data.get("description", "Ödeme"),
            "currency": data.get("currency", "TRY"),
        }

        return vals

    def _auto_reconcile_payment(self, payment):
        """İçe aktarılan ödemeyi uygun açık faturalarla otomatik mutabakata tabi tut."""
        partner = payment.partner_id
        if not partner:
            return False

        # Müşteri tahsilatı ise satış faturaları, tedarikçi ödemesi ise alış faturaları
        allowed_move_types = (
            ("out_invoice", "out_refund")
            if payment.partner_type == "customer"
            else ("in_invoice", "in_refund")
        )

        # Yalnızca post edilmiş ve ödemesi bekleyen faturalar
        invoices = self.env["account.move"].search(
            [
                ("partner_id", "=", partner.id),
                ("state", "=", "posted"),
                ("payment_state", "in", ("not_paid", "partial")),
                ("move_type", "in", list(allowed_move_types)),
            ]
        )

        if not invoices:
            return False

        amount = payment.amount
        tolerance = float(self.payment_reconcile_tolerance or 0.0)
        pay_currency = payment.currency_id or payment.company_id.currency_id

        # Basit kural: aynı para birimli ve kalan tutarı ödemeye eşit olan faturayı bul
        candidate = False
        for inv in invoices:
            inv_currency = inv.currency_id or inv.company_id.currency_id
            if inv_currency.id != pay_currency.id:
                continue
            residual = abs(inv.amount_residual)
            if abs(residual - amount) <= tolerance and residual > 0:
                candidate = inv
                break

        if not candidate:
            return False

        # Mutabakat: alacak/borç satırlarını bulup reconcile et
        def _is_recv_pay_line(line):
            internal_type = getattr(line.account_id, "internal_type", None)
            account_type = getattr(line.account_id, "account_type", None)
            return internal_type in ("receivable", "payable") or account_type in (
                "asset_receivable",
                "liability_payable",
            )

        inv_lines = candidate.line_ids.filtered(
            lambda l: _is_recv_pay_line(l) and not l.reconciled
        )
        pay_lines = payment.move_id.line_ids.filtered(
            lambda l: _is_recv_pay_line(l)
            and not l.reconciled
            and l.partner_id.id == partner.id
        )

        if not inv_lines or not pay_lines:
            return False

        (inv_lines + pay_lines).reconcile()
        _logger.info(
            f"Payment {payment.name} auto-reconciled with invoice {candidate.name}"
        )
        return True

    def _import_invoice(self, data):
        """Tek fatura import et"""
        external_id = str(data.get("id"))

        binding = self.env["bizimhesap.invoice.binding"].search(
            [
                ("backend_id", "=", self.id),
                ("external_id", "=", external_id),
            ],
            limit=1,
        )

        if binding:
            # Fatura zaten var, atla
            return "skipped"

        invoice_vals = self._map_invoice_to_odoo(data)

        if not invoice_vals:
            return "skipped"

        # Faturayı oluştur
        invoice = self.env["account.move"].create(invoice_vals)

        # Faturayı onayla (posted) böylece listelerde doğru görünür
        try:
            invoice.action_post()
        except Exception as e:
            _logger.warning(f"Invoice could not be posted automatically: {e}")

        self.env["bizimhesap.invoice.binding"].create(
            {
                "backend_id": self.id,
                "external_id": external_id,
                "odoo_id": invoice.id,
                "sync_date": fields.Datetime.now(),
                "external_data": json.dumps(data),
            }
        )

        return "created"

    def _map_invoice_to_odoo(self, data):
        """BizimHesap fatura → Odoo account.move dönüşümü"""
        # Partner bul
        contact_id = data.get("contactId")
        partner = None

        if contact_id:
            binding = self.env["bizimhesap.partner.binding"].search(
                [
                    ("backend_id", "=", self.id),
                    ("external_id", "=", str(contact_id)),
                ],
                limit=1,
            )
            if binding:
                partner = binding.odoo_id

        if not partner:
            _logger.warning(
                f"Partner not found for invoice: {data.get('invoiceNumber')}"
            )
            return None

        # Fatura tipi
        invoice_type = data.get("invoiceType", 3)
        # BizimHesap dokümantasyonuna göre: 3=Satış, 5=Alış
        if invoice_type in (3, 1):
            move_type = "out_invoice"
        elif invoice_type in (5,):
            move_type = "in_invoice"
        else:
            move_type = "out_invoice"

        vals = {
            "move_type": move_type,
            "partner_id": partner.id,
            "invoice_date": data.get("invoiceDate"),
            "ref": data.get("invoiceNumber"),
            "narration": data.get("description"),
        }

        # Para birimi (amounts.currency: TL/TRY/EUR/USD ...)
        currency_code = None
        amounts = data.get("amounts") or {}
        if isinstance(amounts, dict):
            currency_code = amounts.get("currency")
        if currency_code:
            code = currency_code
            if code == "TL":
                code = "TRY"
            currency = self.env["res.currency"].search([("name", "=", code)], limit=1)
            if currency:
                vals["currency_id"] = currency.id

        # Journal seçimi (satış/purchase tipine göre)
        journal_type = (
            "sale" if move_type in ("out_invoice", "out_refund") else "purchase"
        )
        journal = self.env["account.journal"].search(
            [
                ("type", "=", journal_type),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )
        if journal:
            vals["journal_id"] = journal.id

        # Fatura kalemleri
        lines = []
        for line_data in data.get("lines", []):
            line_vals = self._map_invoice_line_to_odoo(line_data, move_type)
            if line_vals:
                lines.append((0, 0, line_vals))

        if lines:
            vals["invoice_line_ids"] = lines

        return vals

    def _map_invoice_line_to_odoo(self, data, move_type):
        """Fatura kalemi dönüşümü"""
        # Ürün bul
        product = None
        product_id = data.get("productId")

        if product_id:
            binding = self.env["bizimhesap.product.binding"].search(
                [
                    ("backend_id", "=", self.id),
                    ("external_id", "=", str(product_id)),
                ],
                limit=1,
            )
            if binding:
                product = binding.odoo_id

        vals = {
            "name": data.get("productName", "Ürün"),
            "quantity": float(data.get("quantity", 1)),
            "price_unit": float(data.get("unitPrice", 0)),
        }

        if product:
            vals["product_id"] = product.id

        # KDV
        vat_rate = data.get("vatRate", 20)
        if vat_rate:
            tax_type = "sale" if move_type == "out_invoice" else "purchase"
            tax = self.env["account.tax"].search(
                [
                    ("amount", "=", vat_rate),
                    ("type_tax_use", "=", tax_type),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if tax:
                vals["tax_ids"] = [(6, 0, [tax.id])]

        # Hesap kodu (account_id) fallback: ürün yoksa backend varsayılan hesaplarını kullan
        if not product:
            account = None
            if move_type in ("out_invoice", "out_refund"):
                account = self.default_income_account_id
            else:
                account = self.default_expense_account_id
            if account:
                vals["account_id"] = account.id

        return vals

    # ═══════════════════════════════════════════════════════════════
    # EXPORT METHODS (Odoo → BizimHesap)
    # ═══════════════════════════════════════════════════════════════

    def export_partner(self, partner):
        """Partner'ı BizimHesap'a gönder"""
        self.ensure_one()

        # Mevcut binding kontrol
        binding = self.env["bizimhesap.partner.binding"].search(
            [
                ("backend_id", "=", self.id),
                ("odoo_id", "=", partner.id),
            ],
            limit=1,
        )

        data = self._map_partner_to_bizimhesap(partner)

        if binding:
            # Güncelle
            result = self.update_contact(binding.external_id, data)
        else:
            # Yeni oluştur
            result = self.create_contact(data)

            if result and result.get("id"):
                self.env["bizimhesap.partner.binding"].create(
                    {
                        "backend_id": self.id,
                        "external_id": str(result["id"]),
                        "odoo_id": partner.id,
                        "sync_date": fields.Datetime.now(),
                    }
                )

        return result

    def _map_partner_to_bizimhesap(self, partner):
        """Odoo partner → BizimHesap cari dönüşümü"""
        # Cari tipi belirle
        if partner.customer_rank > 0 and partner.supplier_rank > 0:
            contact_type = 3
        elif partner.supplier_rank > 0:
            contact_type = 2
        else:
            contact_type = 1

        return {
            "code": partner.ref or "",
            "title": partner.name,
            "taxNumber": partner.vat or "",
            "taxOffice": getattr(partner, "l10n_tr_tax_office_name", "") or "",
            "address": partner.street or "",
            "city": partner.city or "",
            "postalCode": partner.zip or "",
            "phone": partner.phone or "",
            "mobile": partner.mobile or "",
            "email": partner.email or "",
            "website": partner.website or "",
            "note": partner.comment or "",
            "contactType": contact_type,
            "currencyCode": "TRY",
        }

    def export_product(self, product):
        """Ürünü BizimHesap'a gönder"""
        self.ensure_one()

        binding = self.env["bizimhesap.product.binding"].search(
            [
                ("backend_id", "=", self.id),
                ("odoo_id", "=", product.id),
            ],
            limit=1,
        )

        data = self._map_product_to_bizimhesap(product)

        if binding:
            result = self.update_product(binding.external_id, data)
        else:
            result = self.create_product(data)

            if result and result.get("id"):
                self.env["bizimhesap.product.binding"].create(
                    {
                        "backend_id": self.id,
                        "external_id": str(result["id"]),
                        "odoo_id": product.id,
                        "sync_date": fields.Datetime.now(),
                    }
                )

        return result

    def _map_product_to_bizimhesap(self, product):
        """Odoo product → BizimHesap ürün dönüşümü"""
        # KDV oranı
        vat_rate = 20
        if product.taxes_id:
            vat_rate = product.taxes_id[0].amount

        return {
            "code": product.default_code or "",
            "name": product.name,
            "description": product.description_sale or "",
            "unit": product.uom_id.name if product.uom_id else "Adet",
            "vatRate": int(vat_rate),
            "purchasePrice": product.standard_price,
            "salePrice": product.list_price,
            "currencyCode": "TRY",
            "stockTracking": product.type == "product",
        }

    def export_invoice(self, invoice):
        """
        Faturayı BizimHesap'a gönder

        BizimHesap B2B API /addinvoice endpoint'i kullanılır.
        InvoiceType: 3=Satış, 5=Alış
        """
        self.ensure_one()
        _logger.info(f"Exporting invoice {invoice.name} to BizimHesap")

        # Fatura zaten gönderilmiş mi?
        if invoice.bizimhesap_guid:
            _logger.warning(f"Invoice {invoice.name} already sent to BizimHesap")
            return {"guid": invoice.bizimhesap_guid, "url": invoice.bizimhesap_url}

        # Fatura verisini hazırla
        data = self._map_invoice_to_bizimhesap(invoice)

        # API'ye gönder
        try:
            response = self._make_request("POST", "/addinvoice", data=data)

            if response.get("error"):
                raise UserError(f"BizimHesap Hata: {response.get('error')}")

            guid = response.get("guid")
            url = response.get("url")

            # Faturayı güncelle
            invoice.write(
                {
                    "bizimhesap_guid": guid,
                    "bizimhesap_url": url,
                    "bizimhesap_sent_date": fields.Datetime.now(),
                }
            )

            # Binding oluştur
            self.env["bizimhesap.invoice.binding"].create(
                {
                    "backend_id": self.id,
                    "external_id": guid,
                    "odoo_id": invoice.id,
                    "sync_date": fields.Datetime.now(),
                    "external_data": json.dumps(data),
                }
            )

            # Log
            self._create_log(
                operation="Export Invoice",
                status="success",
                records_created=1,
                message=f"Fatura {invoice.name} BizimHesap'a gönderildi: {guid}",
            )

            _logger.info(f"Invoice {invoice.name} exported successfully: {guid}")
            return response

        except Exception as e:
            _logger.error(f"Invoice export error: {e}")
            self._create_log(
                operation="Export Invoice",
                status="error",
                records_failed=1,
                message=f"Fatura {invoice.name} gönderilemedi: {str(e)}",
            )
            raise UserError(f"Fatura gönderilemedi: {str(e)}")

    def _map_invoice_to_bizimhesap(self, invoice):
        """
        Odoo account.move → BizimHesap fatura dönüşümü

        BizimHesap B2B API formatı:
        - firmId: API Key
        - invoiceNo: Fatura numarası
        - invoiceType: 3=Satış, 5=Alış
        - dates: {invoiceDate, dueDate, deliveryDate}
        - customer: {customerId, title, address, taxOffice, taxNo, email, phone}
        - amounts: {currency, gross, discount, net, tax, total}
        - details: [{productId, productName, taxRate, quantity, unitPrice, ...}]
        """
        partner = invoice.partner_id

        # Fatura tipi: out_invoice/out_refund = Satış (3), in_invoice/in_refund = Alış (5)
        if invoice.move_type in ("out_invoice", "out_refund"):
            invoice_type = 3  # Satış
        else:
            invoice_type = 5  # Alış

        # Partner binding'den BizimHesap ID al
        partner_binding = self.env["bizimhesap.partner.binding"].search(
            [
                ("backend_id", "=", self.id),
                ("odoo_id", "=", partner.id),
            ],
            limit=1,
        )

        customer_id = partner_binding.external_id if partner_binding else ""

        # Tarihler
        invoice_date = invoice.invoice_date or fields.Date.today()
        due_date = invoice.invoice_date_due or invoice_date

        # Tutar hesapla
        gross = sum(
            line.price_unit * line.quantity for line in invoice.invoice_line_ids
        )
        discount = sum(
            (line.price_unit * line.quantity * line.discount / 100)
            for line in invoice.invoice_line_ids
        )
        net = invoice.amount_untaxed
        tax = invoice.amount_tax
        total = invoice.amount_total

        # Para birimi
        currency = invoice.currency_id.name or "TL"
        if currency == "TRY":
            currency = "TL"

        # Fatura kalemleri
        details = []
        for line in invoice.invoice_line_ids.filtered(lambda l: not l.display_type):
            # Ürün binding'den BizimHesap ID al
            product_id = ""
            if line.product_id:
                product_binding = self.env["bizimhesap.product.binding"].search(
                    [
                        ("backend_id", "=", self.id),
                        ("odoo_id", "=", line.product_id.id),
                    ],
                    limit=1,
                )
                product_id = product_binding.external_id if product_binding else ""

            # KDV oranı
            tax_rate = 20
            if line.tax_ids:
                tax_rate = line.tax_ids[0].amount

            line_gross = line.price_unit * line.quantity
            line_discount = line_gross * line.discount / 100
            line_net = line_gross - line_discount
            line_tax = line_net * tax_rate / 100
            line_total = line_net + line_tax

            details.append(
                {
                    "productId": product_id,
                    "productName": (
                        line.name or line.product_id.name if line.product_id else "Ürün"
                    ),
                    "note": "",
                    "barcode": (
                        line.product_id.barcode
                        if line.product_id and line.product_id.barcode
                        else ""
                    ),
                    "taxRate": f"{tax_rate:.2f}",
                    "quantity": line.quantity,
                    "unitPrice": f"{line.price_unit:,.2f}",
                    "grossPrice": f"{line_gross:,.2f}",
                    "discount": f"{line_discount:,.2f}",
                    "net": f"{line_net:,.2f}",
                    "tax": f"{line_tax:,.2f}",
                    "total": f"{line_total:,.2f}",
                }
            )

        return {
            "firmId": self.api_key,
            "invoiceNo": invoice.name,
            "invoiceType": invoice_type,
            "note": invoice.narration or "",
            "dates": {
                "invoiceDate": invoice_date.strftime("%Y-%m-%dT00:00:00.000+03:00"),
                "dueDate": due_date.strftime("%Y-%m-%dT00:00:00.000+03:00"),
                "deliveryDate": invoice_date.strftime("%Y-%m-%dT00:00:00.000+03:00"),
            },
            "customer": {
                "customerId": customer_id,
                "title": partner.name,
                "taxOffice": getattr(partner, "l10n_tr_tax_office_name", "") or "",
                "taxNo": partner.vat or "",
                "email": partner.email or "",
                "phone": partner.phone or "",
                "address": partner.street or "",
            },
            "amounts": {
                "currency": currency,
                "gross": f"{gross:,.2f}",
                "discount": f"{discount:,.2f}",
                "net": f"{net:,.2f}",
                "tax": f"{tax:,.2f}",
                "total": f"{total:,.2f}",
            },
            "details": details,
        }

    # ═══════════════════════════════════════════════════════════════
    # CRON
    # ═══════════════════════════════════════════════════════════════

    @api.model
    def _cron_sync_all(self):
        """Otomatik senkronizasyon cron job"""
        backends = self.search(
            [
                ("active", "=", True),
                ("state", "=", "connected"),
                ("auto_sync", "=", True),
            ]
        )

        for backend in backends:
            try:
                backend.action_sync_all()
            except Exception as e:
                _logger.error(f"Cron sync failed for {backend.name}: {e}")

    # ═══════════════════════════════════════════════════════════════
    # VIEW ACTIONS
    # ═══════════════════════════════════════════════════════════════

    def action_view_logs(self):
        """Logları görüntüle"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Senkronizasyon Logları"),
            "res_model": "bizimhesap.sync.log",
            "view_mode": "tree,form",
            "domain": [("backend_id", "=", self.id)],
            "context": {"default_backend_id": self.id},
        }

    def action_view_partner_bindings(self):
        """Cari eşleşmelerini görüntüle"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Cari Eşleşmeleri"),
            "res_model": "bizimhesap.partner.binding",
            "view_mode": "tree,form",
            "domain": [("backend_id", "=", self.id)],
        }

    def action_view_product_bindings(self):
        """Ürün eşleşmelerini görüntüle"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Ürün Eşleşmeleri"),
            "res_model": "bizimhesap.product.binding",
            "view_mode": "tree,form",
            "domain": [("backend_id", "=", self.id)],
        }

    def action_view_invoice_bindings(self):
        """Fatura eşleşmelerini görüntüle"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Fatura Eşleşmeleri"),
            "res_model": "bizimhesap.invoice.binding",
            "view_mode": "tree,form",
            "domain": [("backend_id", "=", self.id)],
        }
