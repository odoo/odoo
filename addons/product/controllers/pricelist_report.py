import csv
import io
import json

from werkzeug.exceptions import BadRequest

from odoo import _
from odoo.http import Controller, prepare_content_disposition_header, request, route
from odoo.libs.documents import Document, extension_for, mimetype_for

CSV_MIMETYPE = mimetype_for("csv")
XLSX_MIMETYPE = mimetype_for("xlsx")


class ProductPricelistExportController(Controller):
    @route("/product/export/pricelist/", type="http", auth="user", readonly=True)
    def export_pricelist(self, report_data, export_format):
        if export_format not in ("csv", "xlsx"):
            raise BadRequest("Invalid export format")
        try:
            json_data = json.loads(report_data)
        except ValueError:
            raise BadRequest("Invalid report data") from None
        if not isinstance(json_data, dict):
            raise BadRequest("Invalid report data")
        report_data = request.env[
            "report.product.report_pricelist"
        ]._prepare_pricelist_rendering_context(json_data)
        pricelist_name = report_data["pricelist"]["name"]
        quantities = report_data["quantities"]
        products = report_data["products"]
        headers = [
            _("Product"),
            _("UOM"),
        ] + [_("Quantity (%s UoM)", qty) for qty in quantities]
        if export_format == "csv":
            return self._generate_csv(pricelist_name, quantities, products, headers)
        else:
            return self._generate_xlsx(pricelist_name, quantities, products, headers)

    def _generate_rows(self, products, quantities):
        rows = []
        for product in products:
            variants = product.get("variants", [product])
            for variant in variants:
                row = [variant["name"], variant["uom"]] + [
                    variant["price"].get(qty, 0.0) for qty in quantities
                ]
                rows.append(row)
        return rows

    def _generate_csv(self, pricelist_name, quantities, products, headers):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        rows = self._generate_rows(products, quantities)
        writer.writerows(rows)
        content = buffer.getvalue()
        buffer.close()
        headers = [
            ("Content-Type", CSV_MIMETYPE),
            (
                "Content-Disposition",
                prepare_content_disposition_header(
                    f"Pricelist - {pricelist_name}.{extension_for(CSV_MIMETYPE)}"
                ),
            ),
        ]
        return request.prepare_response(content, headers)

    def _generate_xlsx(self, pricelist_name, quantities, products, headers):
        document = Document.of(
            rows=self._generate_rows(products, quantities),
            mimetype=XLSX_MIMETYPE,
            columns_headers=headers,
            env=request.env,
        )
        return request.prepare_response(
            document.data,
            [
                ("Content-Type", XLSX_MIMETYPE),
                (
                    "Content-Disposition",
                    prepare_content_disposition_header(
                        f"Pricelist - {pricelist_name}.{extension_for(XLSX_MIMETYPE)}"
                    ),
                ),
            ],
        )
