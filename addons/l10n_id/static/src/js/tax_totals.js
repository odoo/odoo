/** @odoo-module **/

import { formatMonetary } from "@web/views/fields/formatters";
import { registry } from "@web/core/registry";
import { TaxTotalsComponent } from "@account/components/tax_totals/tax_totals"

export class TaxTotalsComponentID extends TaxTotalsComponent {

    formatData(props) {
        super.formatData(props);
        
        const currencyFmtOpts = { currencyId: props.record.data.currency_id && props.record.data.currency_id[0] };
        let { subtotals } = JSON.parse(JSON.stringify(props.value));

        // in the original function, the amount will be re-calculated by looping over all subtotal and tax group component 
        // per subtotal. So for the sake of showing it on the widget, we refer to original value of tax_totals field
        // and assign it to JS object
        for(let subtotal_object of subtotals) {
            const name = subtotal_object.name;

            let group = this.totals.groups_by_subtotal[name]
            for(let group_component of group){
                if("dpp_amount" in group_component){
                    group_component["formatted_tax_group_amount"] = formatMonetary(group_component["dpp_amount"], currencyFmtOpts)
                }
            }
        }
    }
}
registry.category("fields").add("account-tax-totals-field-l10n-id", TaxTotalsComponentID);
