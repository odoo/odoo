from odoo import http
from odoo.http import request
import json


class SifRkaDashboardController(http.Controller):

    @http.route(
        "/sif_rka/chart_data",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def get_chart_data(self, tahun=None, coa_id=None):
        """Return chart data for the dashboard bar chart."""
        if not tahun:
            from odoo import fields
            tahun = str(fields.Date.today().year)

        domain = [
            ("rka_id.company_id", "=", request.env.company.id),
            ("tahun", "=", tahun),
        ]
        if coa_id:
            domain.append(("account_id", "=", int(coa_id)))

        monthly_records = request.env["sif.rka.budget.month"].search(
            domain, order="month asc"
        )

        month_names = [
            "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
            "Jul", "Agu", "Sep", "Okt", "Nov", "Des",
        ]

        # Initialize all months with 0
        month_data = {}
        for i in range(1, 13):
            key = str(i).zfill(2)
            month_data[key] = {
                "month": key,
                "label": month_names[i - 1],
                "budget": 0.0,
                "realisasi": 0.0,
            }

        for rec in monthly_records:
            if rec.month in month_data:
                month_data[rec.month]["budget"] += rec.budget_amount or 0.0
                month_data[rec.month]["realisasi"] += rec.realisasi or 0.0

        sorted_months = sorted(month_data.values(), key=lambda x: x["month"])

        labels = [m["label"] for m in sorted_months]
        budget_data = [m["budget"] for m in sorted_months]
        realisasi_data = [m["realisasi"] for m in sorted_months]

        return {
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Anggaran / Pendapatan",
                        "data": budget_data,
                        "backgroundColor": "rgba(41, 98, 255, 0.85)",
                        "borderColor": "rgba(41, 98, 255, 1)",
                        "borderWidth": 1,
                        "borderRadius": 4,
                    },
                    {
                        "label": "Realisasi / Pengeluaran",
                        "data": realisasi_data,
                        "backgroundColor": "rgba(255, 159, 0, 0.85)",
                        "borderColor": "rgba(255, 159, 0, 1)",
                        "borderWidth": 1,
                        "borderRadius": 4,
                    },
                ],
                "tahun": tahun,
                "monthly_details": sorted_months,
            },
        }

    @http.route(
        "/sif_rka/coa_list",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def get_coa_list(self):
        """Return list of COAs for the chart filter."""
        coas = request.env["sif.coa"].search_read(
            [], ["id", "code", "name", "display_name"], order="code asc"
        )
        return {
            "success": True,
            "data": [
                {"id": "", "display_name": "-- Semua COA --"},
            ]
            + [
                {
                    "id": c["id"],
                    "display_name": c["display_name"]
                    or f"[{c['code']}] {c['name']}",
                }
                for c in coas
            ],
        }

    # ============================================================
    # CUSTOM CONTROLLER: Cetak Beban Usaha (tanpa wkhtmltopdf)
    # ============================================================
    @http.route(
        "/sif_rka/print_beban_usaha/<int:record_id>",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def print_beban_usaha(self, record_id=None):
        """Render laporan beban usaha langsung sebagai HTML.

        Solusi ini bypass report system Odoo (qweb-pdf/qweb-html)
        yang membutuhkan wkhtmltopdf untuk PDF. Dengan controller ini:

        - HTML langsung di-render dengan styling lengkap
        - Print CSS untuk Ctrl+P yang sempurna
        - Tidak perlu wkhtmltopdf sama sekali
        - Bisa disimpan sebagai PDF dari browser (Ctrl+P -> Save as PDF)
        """
        record = request.env["sif.rka.budget"].browse(record_id)

        if not record.exists():
            return request.not_found("Record tidak ditemukan.")

        # Ambil data laporan
        report_data = record._get_beban_usaha_report_data()

        if not report_data["rows"]:
            return request.not_found(
                f"Tidak ada data beban usaha untuk tahun "
                f"{report_data['tahun']}."
            )

        # Format currency helper
        def fmt(val):
            return f"{val:,.2f}"

        rows_html = ""
        row_num = 0
        for row in report_data["rows"]:
            row_num += 1
            rows_html += f"""
            <tr>
                <td style="text-align: center; width: 5%;">{row_num}</td>
                <td style="text-align: left; width: 10%;">{row['code']}</td>
                <td style="text-align: left; width: 37%;">{row['name']}</td>
                <td style="text-align: right; width: 24%;">{fmt(row['current_amount'])}</td>
                <td style="text-align: right; width: 24%;">{fmt(row['previous_amount'])}</td>
            </tr>
            """

        total_rows_html = f"""
        <tr style="font-weight: bold; background-color: #ffffff; border-top: 2px solid #000000; border-bottom: 2px solid #000000;">
            <td colspan="3" style="text-align: left;">Total Beban Usaha</td>
            <td style="text-align: right;">{fmt(report_data['total_current_realization'])}</td>
            <td style="text-align: right;">{fmt(report_data['total_previous_realization'])}</td>
        </tr>
        """

        company = request.env.company

        # ===== DATA PERUSAHAAN UNTUK KOP SURAT =====
        company_name = company.name or 'PERUSAHAAN'

        # Alamat
        addr_parts = []
        if company.street:
            addr_parts.append(company.street)
        if company.street2:
            addr_parts.append(company.street2)
        if company.city:
            addr_parts.append(company.city)
        if company.state_id:
            addr_parts.append(company.state_id.name)
        if company.zip:
            addr_parts.append(company.zip)
        company_addr = ', '.join(addr_parts) if addr_parts else ''

        company_phone = company.phone or ''
        company_email = company.email or ''
        company_website = company.website or ''
        company_vat = company.vat or ''

        # ===== LOGO (BASE64) =====
        logo_html = ''
        if company.logo:
            import base64
            logo_b64 = company.logo.decode('utf-8') if isinstance(company.logo, bytes) else company.logo
            logo_html = f'''
            <div style="flex: 0 0 85px;">
                <img src="data:image/png;base64,{logo_b64}" alt="Logo" style="max-width: 85px; max-height: 85px; display: block;" />
            </div>
            '''

        # ===== KONTEN DETAIL PERUSAHAAN DI KOP =====
        kop_detail_parts = []
        if company_addr:
            kop_detail_parts.append(company_addr)
        if company_phone:
            kop_detail_parts.append(f'Tlp. {company_phone}')
        if company_email:
            kop_detail_parts.append(f'Email: {company_email}')
        if company_website:
            kop_detail_parts.append(company_website)
        if company_vat:
            kop_detail_parts.append(f'NPWP: {company_vat}')

        kop_details = ' &nbsp;&nbsp;|&nbsp;&nbsp; '.join(kop_detail_parts) if kop_detail_parts else ''

        # ===== TANGGAL =====
        from odoo import fields as od_fields
        now = od_fields.Datetime.now()
        month_names_id = [
            'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ]
        city = company.city or 'Jakarta'
        tanggal_laporan = f"{city}, {now.day} {month_names_id[now.month - 1]} {now.year}"
        user_name = request.env.user.display_name or 'Admin'

        html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<title>Laporan Beban Usaha - {report_data['tahun']}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
        font-family: 'Times New Roman', 'DejaVu Serif', Georgia, serif;
        font-size: 11pt;
        color: #000000;
        line-height: 1.6;
        padding: 20px 30px;
        background: white;
    }}

    /* ===== KOP SURAT ===== */
    .letterhead {{
        display: flex;
        align-items: center;
        gap: 20px;
        padding-bottom: 12px;
        border-bottom: 3px double #000000;
        margin-bottom: 18px;
    }}

    .letterhead .company-name {{
        font-size: 16pt;
        font-weight: bold;
        color: #000000;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        line-height: 1.2;
        margin-bottom: 2px;
    }}

    .letterhead .kop-sub {{
        font-size: 9pt;
        color: #000000;
        font-style: italic;
        margin-bottom: 3px;
    }}

    .letterhead .kop-details {{
        font-size: 8pt;
        color: #000000;
        line-height: 1.6;
    }}

    /* ===== JUDUL ===== */
    .title-section {{
        text-align: center;
        margin-bottom: 15px;
    }}

    .title-section h1 {{
        font-size: 14pt;
        font-weight: bold;
        color: #000000;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 2px;
    }}

    .title-section .sub-title {{
        font-size: 10pt;
        color: #000000;
    }}

    /* ===== TABLE ===== */
    .data-table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 15px;
        font-size: 10pt;
    }}

    .data-table thead th {{
        background-color: #ffffff;
        color: #000000;
        padding: 7px 6px;
        text-align: center;
        font-weight: bold;
        font-size: 9.5pt;
        border: 1px solid #000000;
        text-transform: uppercase;
    }}

    .data-table thead th:first-child {{
        text-align: center;
    }}

    .data-table tbody td {{
        padding: 5px 6px;
        border: 1px solid #000000;
        vertical-align: middle;
        font-size: 10pt;
        color: #000000;
    }}

    .data-table tbody tr {{
        background-color: #ffffff;
    }}

    .data-table .total-row td {{
        font-weight: bold;
        background-color: #ffffff;
        border-top: 2px solid #000000;
        border-bottom: 2px solid #000000;
        padding: 7px 6px;
        font-size: 10pt;
        color: #000000;
    }}

    /* ===== TANDA TANGAN ===== */
    .signature-section {{
        display: flex;
        justify-content: space-between;
        margin-top: 50px;
        padding: 0 40px;
    }}

    .signature-box {{
        text-align: center;
        width: 45%;
    }}

    .signature-box .sig-role {{
        font-size: 9pt;
        color: #000000;
        margin-bottom: 5px;
    }}

    .signature-box .sig-line {{
        margin-top: 50px;
        margin-bottom: 3px;
        border-top: 1px solid #000000;
        width: 100%;
    }}

    .signature-box .sig-name {{
        font-size: 10pt;
        font-weight: bold;
        color: #000000;
    }}

    .signature-box .sig-title {{
        font-size: 9pt;
        color: #000000;
        margin-top: 1px;
    }}

    /* ===== FOOTER ===== */
    .footer {{
        margin-top: 20px;
        text-align: center;
        font-size: 7.5pt;
        color: #000000;
        border-top: 1px solid #000000;
        padding-top: 6px;
    }}

    /* ===== PRINT STYLES (A4 PORTRAIT) ===== */
    @media print {{
        @page {{
            size: A4;
            margin: 20mm 15mm 20mm 15mm;
        }}
        body {{
            padding: 0;
            font-size: 10pt;
            color: #000000;
        }}
        .letterhead {{
            border-bottom: 3px double #000000 !important;
        }}
        .data-table thead th {{
            background-color: #ffffff !important;
            color: #000000 !important;
        }}
        .data-table tbody td {{
            border-color: #000000 !important;
            color: #000000 !important;
        }}
        .data-table tbody tr {{
            background-color: #ffffff !important;
        }}
        .data-table .total-row td {{
            background-color: #ffffff !important;
            border-top: 2px solid #000000 !important;
            border-bottom: 2px solid #000000 !important;
        }}
        .data-table {{
            page-break-inside: auto;
        }}
        tr {{
            page-break-inside: avoid;
            page-break-after: auto;
        }}
        thead {{
            display: table-header-group;
        }}
        .no-print {{
            display: none !important;
        }}
    }}

    @media screen {{
        body {{
            max-width: 900px;
            margin: 20px auto;
            box-shadow: 0 2px 15px rgba(0,0,0,0.1);
            border-radius: 3px;
        }}
    }}

    .no-print {{
        text-align: center;
        margin-top: 15px;
    }}
    .no-print button {{
        padding: 10px 30px;
        background: #333333;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 11pt;
        font-family: 'Times New Roman', serif;
    }}
    .no-print button:hover {{
        background: #555555;
    }}
    .no-print .hint {{
        margin-top: 5px;
        font-size: 9pt;
        color: #000000;
        font-family: 'Times New Roman', serif;
    }}
</style>
</head>
<body>

<!-- KOP SURAT -->
<div class="letterhead">
    {logo_html if logo_html else ''}
    <div class="kop-content">
        <div class="company-name">{company_name}</div>
        <div class="kop-sub">Laporan Keuangan Manajemen &mdash; Beban Usaha</div>
        {('<div class="kop-details">' + kop_details + '</div>') if kop_details else ''}
    </div>
</div>

<!-- JUDUL -->
<div class="title-section">
    <h1>Laporan Beban Usaha</h1>
    <div class="sub-title">
        Untuk Tahun yang Berakhir pada 31 Desember {report_data['tahun']} dan {report_data['tahun_sebelumnya']}
    </div>
</div>

<!-- TABLE -->
<table class="data-table">
    <thead>
        <tr>
            <th style="width: 5%;">No</th>
            <th style="width: 10%;">Kode</th>
            <th style="width: 37%; text-align: left;">Nama Akun</th>
            <th style="width: 24%;">{report_data['tahun']}<br><span style="font-weight: normal; font-size: 7.5pt; color: #000000;">(Rp)</span></th>
            <th style="width: 24%;">{report_data['tahun_sebelumnya']}<br><span style="font-weight: normal; font-size: 7.5pt; color: #000000;">(Rp)</span></th>
        </tr>
    </thead>
    <tbody>
        {rows_html}
        {total_rows_html}
    </tbody>
</table>

<!-- TANDA TANGAN -->
<div class="signature-section">
    <div class="signature-box">
        <div class="sig-role">Mengetahui,</div>
        <div class="sig-role">Direktur Utama</div>
        <div class="sig-line"></div>
        <div class="sig-name">{company_name}</div>
        <div class="sig-title">Direktur Utama</div>
    </div>
    <div class="signature-box">
        <div class="sig-role">{tanggal_laporan}</div>
        <div class="sig-role">Penyusun</div>
        <div class="sig-line"></div>
        <div class="sig-name">{user_name}</div>
        <div class="sig-title">Penyusun Laporan</div>
    </div>
</div>

<!-- FOOTER -->
<div class="footer">
    Laporan Beban Usaha {report_data['tahun']} &mdash; {company_name} &mdash; Dicetak: {tanggal_laporan}
</div>

<!-- TOMBOL CETAK -->
<div class="no-print">
    <button onclick="window.print()">Cetak / Simpan PDF (Ctrl+P)</button>
    <div class="hint">Gunakan tombol di atas, lalu pilih &quot;Save as PDF&quot; di printer tujuan</div>
</div>

</body>
</html>"""

        return request.make_response(
            html,
            headers=[
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Disposition",
                 f'inline; filename="beban_usaha_{report_data["tahun"]}.html"'),
            ],
        )
