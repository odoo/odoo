from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, res_ids=None, data=None, run_script=None):
        account_move = self.env[self.model].browse(res_ids)
        if account_move.company_id.country_id.code != 'PT':
            return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
        carrying_text = "Valor acumulado"
        currency_decimal_places = account_move.currency_id.decimal_places
        currency_symbol = account_move.currency_id.symbol
        currency_symbol_code = ord(currency_symbol)
        currency_position = account_move.currency_id.position
        run_script = f"""
            // Constants for A4 paper size
            const tableWidth = "17.65cm";
            const firstPageEnd = 3050;
            const bodyHeight = 580;

            // Force the HTML and the PDF table (and its columns) to have the same width across all pages
            // (because the table header will be copied for each of the future tables)
            // This is necessary to correctly determine which table row belongs to which page
            const originalTable = document.querySelector("table");
            originalTable.style.width = tableWidth;
            const ths = originalTable.querySelectorAll("th");
            for (var i = 0; i < ths.length; i++) {{
                ths[i].style.width = ths[i].getBoundingClientRect().width + "px";
            }}
            
            // Parse main table informations into a list of dicts representing the smaller tables (one per page)
            const rows = originalTable.querySelectorAll("tbody>tr");
            var tables = [{{
                rows: [],
                carrying: 0.0,
            }}]
            for (var i = 0; i < rows.length; i++) {{
                tables[tables.length-1].rows.push(i);
                tables[tables.length-1].carrying += parseFloat(rows[i].querySelector("span[data-amount]").getAttribute("data-amount"));
                if (rows[i].getBoundingClientRect().bottom > firstPageEnd + (tables.length-1) * bodyHeight) {{
                    tables.push({{
                        rows: [],
                        carrying: tables[tables.length-1].carrying,
                    }})
                }}
            }}
            
            // Delete the old unique table (but remember its header to reuse it later)
            const theadElement = document.querySelector("thead");
            originalTable.parentNode.removeChild(originalTable);
            
            // Function to create the div containing the carry over in the beggining/end of the page
            function carryValueElement(amount) {{
                var formattedAmount = amount.toFixed({currency_decimal_places});
                if ("{currency_position}" == "after")
                    formattedAmount += "&nbsp;&#{currency_symbol_code}"
                else
                    formattedAmount = "&#{currency_symbol_code}&nbsp;" + formattedAmount
                return "<table class='table-sm' style='margin-left: auto; margin-right: 0; border-top: 1px solid; border-bottom: 1px solid'>"+
                            "<tr>" +
                                "<td><strong>{carrying_text}</strong></td>" +
                                "<td class='text-right'>" +
                                    "<strong>" + formattedAmount + "</strong>" +
                                "</td>" +
                            "</tr>" +
                        "</table>" 
            }}
            
            // Create the new tables
            for (var i = 0; i < tables.length; i++){{
                var html = "";
                if (i != 0) 
                    html += carryValueElement(tables[i-1].carrying);
                if (tables[i].rows.length > 0){{
                    html += "<table class='table table-sm o_main_table' name='invoice_line_table' style='width: " + tableWidth + "'>";
                    html +=     theadElement.outerHTML;
                    html += "   <tobdy>";
                    for (var j = 0; j < tables[i].rows.length; j++){{
                        const row = rows[tables[i].rows[j]];
                        html += row.outerHTML;
                    }}
                    html += "   </tbody>";
                    html += "</table>";
                }}
                if (i != tables.length - 1) {{
                    html += carryValueElement(tables[i].carrying);
                    html += "<div style='page-break-after: always;'/>";
                }}
                document.getElementById("total").parentNode.insertAdjacentHTML("beforebegin", html);
            }}
        """
        return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
