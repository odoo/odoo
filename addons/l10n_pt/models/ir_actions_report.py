from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, res_ids=None, data=None, run_script=None):
        account_move = self.env[self.model].browse(res_ids)
        if account_move.company_id.country_id.code != 'PT':
            return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
        run_script = """
            var rows = document.querySelectorAll('tr');
            
            //For each row, add the distance between beginning and the bottom of the row as an attribute
            for (var i = 1; i < rows.length; i++) {
                var row = rows[i];
                var bottom = row.getBoundingClientRect().bottom;
                row.setAttribute('data-bottom', bottom);
                var first_child = row.querySelector("td");
                if (first_child != undefined){  
                    first_child.innerText += " (b: " + bottom + ")";
                }
            }
            
            const thead_bottom = document.querySelector("thead").getBoundingClientRect().bottom;
            document.querySelector("thead").style.display = "table-row-group";
            const nb_columns = document.querySelectorAll("th").length;
            const first_page_height = 1000;
            const page_height = 2000;
            var carrying = 0.0;
            var nb_pages = 0;
            
            //Split table in pages and add the carryover
            for (var i = 1; i < rows.length; i++) {
                var row = rows[i];
                var bottom = row.getAttribute('data-bottom');
                const amount = document.querySelectorAll('span.oe_currency_value')[i-1].innerText;
                carrying += parseFloat(amount.split(",").join(""));
                if ( (nb_pages == 0 && bottom > first_page_height + thead_bottom) ||
                     (nb_pages > 0  && bottom - nb_pages * page_height > page_height + first_page_height) ) { 
                    nb_pages += 1;
                    td_repeat = ''
                    for (var j = 0; j < nb_columns-2; j++) {
                        td_repeat += '<td> </td>';
                    }
                    const carrying_text = carrying.toFixed(2) + '&euro;';
                    row.insertAdjacentHTML('afterend', '<tr class="text-right font-weight-bold">' + td_repeat + '<td> Carrying: </td> <td>' + carrying_text + '</td></tr></tbody></table> <div style="page-break-before: always;">BREAK</div> <table><thead><tr><th>Description2</th><th>Quantity2</th><th>Unit price2</th><th>Taxes2</th><th>Amount2</th></tr></thead><tbody><tr class="text-right font-weight-bold">' + td_repeat + '<td> Carried: </td> <td>' + carrying_text + '</td></tr>');
                }
            }
            rows[rows.length-1].insertAdjacentHTML('afterend', '</tbody></table>');
        """
        return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
