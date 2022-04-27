from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, res_ids=None, data=None, run_script=None):
        account_move = self.env[self.model].browse(res_ids)
        if account_move.company_id.country_id.code != 'PT':
            return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
        run_script = """
            // Get all necessary elements and data
            var rows = document.querySelectorAll("tr");
            var amounts = document.querySelectorAll("span.oe_currency_value");
            
            const theader = document.querySelector("thead")
            const theadBottom = document.querySelector("thead").getBoundingClientRect().bottom;
            const firstPageHeight = 1000;
            const pageHeight = 2000;
            
            //For each row, add the distance between beginning and the bottom of the row as an attribute
            for (var i = 1; i < rows.length; i++) {
                var row = rows[i];
                var bottom = row.getBoundingClientRect().bottom;
                row.setAttribute("data-bottom", bottom);
            }
            
            //Split main table in multiple smaller tables
            tables = [{
                page: 0,
                rows: [],
                to_carry: 0.0,
            }]
            for (var i = 1; i < rows.length; i++) {
                var row = rows[i];
                const bottom = row.getAttribute("data-bottom");
                if (amounts[i - 1] === undefined) //i-1 because we skip the header
                    continue
                tables[tables.length-1].to_carry += parseFloat(amounts[i - 1].innerText.split(",").join(""));
                tables[tables.length-1].rows.push(i);
                if ((tables.length == 1 && bottom > firstPageHeight + theadBottom) || //First page
                    (tables.length > 1 && bottom - (tables.length-1) * pageHeight > pageHeight + firstPageHeight)) { //Other pages
                    tables.push({
                        page: tables.length,
                        rows: [],
                        to_carry: tables[tables.length-1].to_carry,
                    })
                }
            }
            
            // Delete the old mainTable
            const mainTable = document.querySelector("table");
            mainTable.parentNode.removeChild(mainTable);
            
            function carryValueElement(amount) {
                return "<div class='text-bold text-right'>" + 
                            "Valor acumulado: " + amount.toFixed(2) + "&euro;" + 
                       "</div>"
            }
            
            // Create the new tables
            console.log(JSON.stringify(tables));
            for (var i = 0; i < tables.length; i++){
                var html = "";
                if (i != 0) 
                    html += carryValueElement(tables[i-1].to_carry);
                html += "<table class='table table-sm o_main_table' name='invoice_line_table'>";
                html +=     theader.outerHTML;
                html += "   <tobdy>";
                for (var j = 0; j < tables[i].rows.length; j++){
                    const row = rows[tables[i].rows[j]];
                    html += row.outerHTML;
                }
                html += "   </tbody>";
                html += "</table>";
                if (i != tables.length - 1) {
                    html += carryValueElement(tables[i].to_carry);
                    html += "<div style='page-break-after: always;'/>";
                }
                const totalElement = document.getElementById("total").parentNode;
                totalElement.insertAdjacentHTML("beforebegin", html);
            }

            //console.log(document.body.innerHTML);
        """
        return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
