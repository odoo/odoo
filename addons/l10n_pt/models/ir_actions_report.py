from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, res_ids=None, data=None, run_script=None):
        account_move = self.env[self.model].browse(res_ids)
        if account_move.company_id.country_id.code != 'PT':
            return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
        run_script = """
            var rows = document.querySelectorAll("tr");
            var amounts = document.querySelectorAll("span.oe_currency_value");
            const theader = document.querySelector("thead")
            
            //For each row, add the distance between beginning and the bottom of the row as an attribute
            for (var i = 1; i < rows.length; i++) {
                var row = rows[i];
                var bottom = row.getBoundingClientRect().bottom;
                row.setAttribute("data-bottom", bottom);
            }
            
            const thead_bottom = document.querySelector("thead").getBoundingClientRect().bottom;
            const nb_columns = document.querySelectorAll("th").length;
            const first_page_height = 1000;
            const page_height = 2000;
            var carrying = 0.0;
            var nb_pages = 0;
            
            //Split table in pages
            tables = [{
                page: 0,
                rows: [],
                to_carry: 0.0,
                last_bottom: 0,
            }]
            for (var i = 1; i < rows.length; i++) {
                var row = rows[i];
                const bottom = row.getAttribute("data-bottom");
                if (amounts[i - 1] === undefined) //i-1 because we skip the header
                    continue
                tables[tables.length-1].to_carry += parseFloat(amounts[i - 1].innerText.split(",").join(""));
                tables[tables.length-1].rows.push(i);
                tables[tables.length-1].last_bottom = bottom;
                if ((nb_pages == 0 && bottom > first_page_height + thead_bottom) ||
                    (nb_pages > 0 && bottom - nb_pages * page_height > page_height + first_page_height)) {
                    nb_pages += 1;
                    tables.push({
                        page: nb_pages,
                        rows: [],
                        to_carry: tables[tables.length-1].to_carry,
                        last_bottom: 0,
                    })
                }
            }
            console.log(JSON.stringify(tables));
            const mainTable = document.querySelector("table");
            mainTable.parentNode.removeChild(mainTable);

            
            // Create the new tables
            for (var i = 0; i < tables.length; i++){
                console.log("Creating table " + JSON.stringify(tables[i]));
                var html = "";
                if (i != 0) 
                    html += "<div class='muted text-right'>Carried:" + tables[i-1].to_carry + " </div>";
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
                    html += "<div class='muted text-right'>Carrying:" + tables[i].to_carry + " </div>";
                    html += "<div style='page-break-after: always; background-color: red;'>--BREAK--</div>";
                }
                const sibling = document.getElementById("total").parentNode;
                sibling.insertAdjacentHTML("beforebegin", html);
            }

            //console.log(document.body.innerHTML);
        """
        return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
