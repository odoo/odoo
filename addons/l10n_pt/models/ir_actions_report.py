from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, res_ids=None, data=None, run_script=None):
        account_move = self.env[self.model].browse(res_ids)
        if account_move.company_id.country_id.code != 'PT':
            return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
        run_script = """
            // Constants in 10*mm (for A4 format)
            const pageHeight = 2970;
            const firstHeaderHeight = 1200;
            const headerHeight = 500;
            const footerHeight = 400;
            const carryOverHeight = 200;
            
            const firstBodyHeight = pageHeight - firstHeaderHeight - footerHeight - carryOverHeight;
            const bodyHeight = pageHeight - headerHeight - footerHeight - carryOverHeight;
            
            // Parse main table informations into a list of dicts representing the smaller tables (one per page)
            const rows = document.querySelectorAll("tr");
            const amounts = document.querySelectorAll("span.oe_currency_value");
            var tables = [{
                rows: [],
                carrying: 0.0,
            }]
            for (var i = 1; i < rows.length; i++) {
                if (amounts[i - 1] === undefined)   // i-1 because offset with header which has no amount,
                    continue                        // might be undefined if the row is a total row
                tables[tables.length-1].carrying += parseFloat(amounts[i - 1].innerText.split(",").join(""));
                tables[tables.length-1].rows.push(i);
                
                const bottom = rows[i].getBoundingClientRect().bottom;
                const firstPageEnd = pageHeight + firstBodyHeight;
                if ((tables.length == 1 && bottom > firstPageEnd) || //First page
                    (tables.length > 1  && bottom > firstPageEnd + firstHeaderHeight - headerHeight + (tables.length-1) * bodyHeight)) { //Other pages
                    tables.push({
                        rows: [],
                        carrying: tables[tables.length-1].carrying,
                    })
                }
            }
            
            // Delete the old mainTable (but remember its header to reuse later)
            const tableElement = document.querySelector("table");
            const theadElement = document.querySelector("thead").cloneNode();
            tableElement.parentNode.removeChild(tableElement);
            
            // Function to create the div containing the carry over in the beggining/end of the page
            function carryValueElement(amount) {
                return "<div class='text-bold text-right'>" + 
                            "Valor acumulado: " + amount.toFixed(2) + "&euro;" + 
                       "</div>"
            }
            
            // Create the new tables
            for (var i = 0; i < tables.length; i++){
                var html = "";
                if (i != 0) 
                    html += carryValueElement(tables[i-1].carrying);
                html += "<table class='table table-sm o_main_table' name='invoice_line_table'>";
                html +=     theadElement.outerHTML;
                html += "   <tobdy>";
                for (var j = 0; j < tables[i].rows.length; j++){
                    const row = rows[tables[i].rows[j]];
                    html += row.outerHTML;
                }
                html += "   </tbody>";
                html += "</table>";
                if (i != tables.length - 1) {
                    html += carryValueElement(tables[i].carrying);
                    html += "<div style='page-break-after: always;'/>";
                }
                document.getElementById("total").parentNode.insertAdjacentHTML("beforebegin", html);
            }
        """
        return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
