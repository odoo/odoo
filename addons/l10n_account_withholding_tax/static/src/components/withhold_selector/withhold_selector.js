import { registry } from "@web/core/registry";
import { radioField, RadioField } from "@web/views/fields/radio/radio_field";
import { deepCopy } from "@web/core/utils/objects";

export class WithholdSelector extends RadioField {
    static template = "web.RadioField";
    
    get items() {
        let items = deepCopy(super.items);
        if (!(this.props.record.data.reconciled_bills_count || this.props.record.data.reconciled_invoices_count)) {
            items = items.filter(
                (item) => item[0] !== "withhold"
            );
        }
        return items;
    }
}

export const withholdSelector = {
    ...radioField,
    additionalClasses: ["o_field_radio"],
    component: WithholdSelector,
    extractProps() {
        return radioField.extractProps(...arguments);
    },
};

registry.category("fields").add("withhold_selector", withholdSelector);
