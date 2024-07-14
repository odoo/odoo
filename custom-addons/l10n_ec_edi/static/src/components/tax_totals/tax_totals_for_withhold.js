/** @odoo-module **/
import { registry } from "@web/core/registry";
import { TaxTotalsComponent } from "@account/components/tax_totals/tax_totals";

/**
 * Tax totals component specific to withholds.
 * In withholds, the base is not included in the total.
 * The base may be displayed to keep accountants happy, for example as part of the formatted values.
 */
export class TaxTotalsComponentForWithhold extends TaxTotalsComponent {
    formatData(props) {
        // Prevents super's formatting method from running
        // (its logic is not compatible with withholds)
        this.totals = props.record.data[this.props.name];
    }
}

registry.category("fields").add("account-tax-totals-field-for-withhold", {
    component: TaxTotalsComponentForWithhold
});
