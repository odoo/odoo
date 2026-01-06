# -*- coding: utf-8 -*-

import json

from odoo import _, api, fields, models


class BizimHesapCustomerAbstractWizard(models.TransientModel):
    """
    BizimHesap Cari Hesap Ekstresi Görüntüleme Wizard
    """

    _name = "bizimhesap.customer.abstract.wizard"
    _description = "BizimHesap Cari Ekstre Görüntüleyici"

    partner_id = fields.Many2one(
        "res.partner",
        string="Cari",
        required=True,
        readonly=True,
    )

    backend_id = fields.Many2one(
        "bizimhesap.backend",
        string="BizimHesap Bağlantısı",
        required=True,
        readonly=True,
    )

    external_id = fields.Char(
        string="BizimHesap ID",
        readonly=True,
    )

    abstract_data = fields.Text(
        string="Ekstre Verileri (JSON)",
        readonly=True,
    )

    balance = fields.Float(
        string="Cari Bakiye",
        digits=(16, 2),
        readonly=True,
    )

    currency = fields.Char(
        string="Para Birimi",
        readonly=True,
        default="TRY",
    )

    abstract_html = fields.Html(
        string="Hesap Ekstresi",
        compute="_compute_abstract_html",
    )

    @api.depends("abstract_data")
    def _compute_abstract_html(self):
        """
        JSON verisini HTML tablosuna çevir
        """
        for wizard in self:
            if not wizard.abstract_data:
                wizard.abstract_html = "<p>Veri yok</p>"
                continue

            try:
                data = (
                    eval(wizard.abstract_data)
                    if isinstance(wizard.abstract_data, str)
                    else wizard.abstract_data
                )

                html = '<div style="font-family: Arial, sans-serif;">'
                html += f"<h3>📊 Cari Hesap Ekstresi: {wizard.partner_id.name}</h3>"
                html += f"<p><strong>BizimHesap ID:</strong> {wizard.external_id}</p>"

                # Bakiye bilgisi
                balance = data.get("balance", 0.0)
                currency = data.get("currency", "TRY")
                balance_color = "green" if balance >= 0 else "red"
                html += f'<p><strong>Bakiye:</strong> <span style="color: {balance_color}; font-size: 18px; font-weight: bold;">{balance:,.2f} {currency}</span></p>'

                # Çek/Senet bilgisi
                if "cheque_bond" in data:
                    html += f'<p><strong>Çek/Senet:</strong> {data["cheque_bond"]:,.2f} {currency}</p>'

                # Hareketler tablosu
                transactions = data.get("transactions", [])
                if transactions:
                    html += "<h4>📋 Hesap Hareketleri</h4>"
                    html += '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">'
                    html += '<thead><tr style="background-color: #f0f0f0;">'
                    html += '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Tarih</th>'
                    html += '<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">İşlem</th>'
                    html += '<th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Borç</th>'
                    html += '<th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Alacak</th>'
                    html += '<th style="border: 1px solid #ddd; padding: 8px; text-align: right;">Bakiye</th>'
                    html += "</tr></thead><tbody>"

                    for txn in transactions:
                        html += "<tr>"
                        html += f'<td style="border: 1px solid #ddd; padding: 8px;">{txn.get("date", "-")}</td>'
                        html += f'<td style="border: 1px solid #ddd; padding: 8px;">{txn.get("description", "-")}</td>'
                        html += f'<td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{txn.get("debit", 0):,.2f}</td>'
                        html += f'<td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{txn.get("credit", 0):,.2f}</td>'
                        html += f'<td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{txn.get("balance", 0):,.2f}</td>'
                        html += "</tr>"

                    html += "</tbody></table>"
                else:
                    html += "<p><em>Henüz hareket kaydı yok</em></p>"

                # Ham veri (debug için)
                html += '<hr style="margin-top: 20px;">'
                html += '<details><summary style="cursor: pointer; color: #666;">🔍 Ham Veri (Teknik Detay)</summary>'
                html += f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow: auto;">{json.dumps(data, indent=2, ensure_ascii=False)}</pre>'
                html += "</details>"

                html += "</div>"
                wizard.abstract_html = html

            except Exception as e:
                wizard.abstract_html = f'<p style="color: red;">Veri işlenirken hata: {str(e)}</p><pre>{wizard.abstract_data}</pre>'

    def action_refresh(self):
        """
        Ekstre verilerini yenile
        """
        self.ensure_one()

        try:
            result = self.backend_id.get_customer_abstract(self.external_id)

            if result and "error" not in result:
                self.write(
                    {
                        "abstract_data": str(result),
                        "balance": result.get("balance", 0.0),
                        "currency": result.get("currency", "TRY"),
                    }
                )

                # Partner üzerinde bakiye alanlarını güncelle
                partner_updates = {
                    "bizimhesap_balance": result.get("balance", 0.0),
                    "bizimhesap_cheque_bond": result.get("cheque_bond", 0.0),
                    "bizimhesap_currency": result.get("currency", "TRY"),
                    "bizimhesap_last_balance_update": fields.Datetime.now(),
                }
                self.partner_id.write(partner_updates)

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Başarılı"),
                        "message": _("Ekstre verileri güncellendi!"),
                        "type": "success",
                        "sticky": False,
                    },
                }
            else:
                error_msg = (
                    result.get("error", "Bilinmeyen hata")
                    if result
                    else "API yanıt vermedi"
                )
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Hata"),
                        "message": f"Ekstre güncellenemedi: {error_msg}",
                        "type": "danger",
                        "sticky": True,
                    },
                }

        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Hata"),
                    "message": f"Güncelleme hatası: {str(e)}",
                    "type": "danger",
                    "sticky": True,
                },
            }
