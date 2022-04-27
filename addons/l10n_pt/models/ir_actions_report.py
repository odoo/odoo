from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, res_ids=None, data=None, run_script=None):
        account_move = self.env[self.model].browse(res_ids)
        if account_move.company_id.country_id.code != 'PT':
            return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
        run_script = """
            // Page elements
            const addressHeight = document.querySelector('.address').parentNode.getBoundingClientRect().height;
            const titleHeight = document.querySelector('h2').getBoundingClientRect().height;
            const informationsHeight = document.querySelector('#informations').getBoundingClientRect().height;
            
            // Table elements
            const tableElement = document.querySelector("table");
            const tableBottom = tableElement.getBoundingClientRect().bottom;
            const theadElement = document.querySelector("thead")
            const theadHeight = theadElement.getBoundingClientRect().height;
            const totalElement = document.getElementById("total").parentNode;
            
            // Constants
            const pageHeight = 1500;
            const firstPageHeight = pageHeight + addressHeight + titleHeight + informationsHeight - theadHeight;
            const lastPageHeight = 0; //TODO
            
            // Prints
            console.log("addressHeight: " + addressHeight);
            console.log("titleHeight: " + titleHeight);
            console.log("informationsHeight: " + informationsHeight);
            console.log("pageHeight: " + pageHeight);
            console.log("theadHeight: " + theadHeight);
            console.log("firstPageHeight: " + firstPageHeight);
            
            // Parse main table informations into a list of dicts representing the smaller tables (one per page)
            const rows = document.querySelectorAll("tr");
            const amounts = document.querySelectorAll("span.oe_currency_value");
            tables = [{
                page: 0,
                rows: [],
                to_carry: 0.0,
                bottoms: [],
            }]
            for (var i = 1; i < rows.length; i++) {
                var row = rows[i];
                const bottom = row.getBoundingClientRect().bottom;
                row.querySelector("td") != undefined ? row.querySelector("td").innerText += " (b: " + bottom + ")" : null; // TO REMOVE
                if (amounts[i - 1] === undefined) //i-1 because we skip the header, undefined if the row is a total
                    continue
                tables[tables.length-1].to_carry += parseFloat(amounts[i - 1].innerText.split(",").join(""));
                tables[tables.length-1].rows.push(i);
                tables[tables.length-1].bottoms.push(bottom);
                if ((tables.length == 1 && bottom > firstPageHeight) || //First page
                    (tables.length > 1  && bottom > (tables.length-1) * pageHeight + firstPageHeight)) { //Other pages
                    tables.push({
                        page: tables.length,
                        rows: [],
                        to_carry: tables[tables.length-1].to_carry,
                        bottoms: [],
                    })
                }
            }
            
            // Delete the old mainTable
            tableElement.parentNode.removeChild(tableElement);
            
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
                html +=     theadElement.outerHTML;
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
                totalElement.insertAdjacentHTML("beforebegin", html);
            }

            //console.log(document.body.innerHTML);
        """
        return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
