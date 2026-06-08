import { localeCompare } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";
import { RadioField } from "@web/views/fields/radio/radio_field";

export class OrderedRadioField extends RadioField {
    get items() {
        let items = super.items;
        if (this.type == 'selection') {
            return items.sort((a, b) => {
                if (a[0] === 'other') return 1;  // "other" goes last
                if (b[0] === 'other') return -1;
                return localeCompare(a[0], b[0]);  // alphabetical for the rest
            });
        }
        return items;
    }
}

registry.category("fields").add("ordered_radio", {
    ...registry.category("fields").get("radio"),
    component: OrderedRadioField,
});
