import { registry } from "@web/core/registry";
import { RadioField } from "@web/views/fields/radio/radio_field";

export class OrderedRadioField extends RadioField {
    get items() {
        let items = super.items;
        if (this.type == 'selection') {
            const order = {
                department: 0,
                employee: 1,
                vehicle: 2,
                other: 100,
            };
            return items.sort((a, b) => {
                const aRank = order[a[0]] ?? 99;
                const bRank = order[b[0]] ?? 99;
                return aRank - bRank;
            });
        }
        return items;
    }
}

registry.category("fields").add("ordered_radio", {
    ...registry.category("fields").get("radio"),
    component: OrderedRadioField,
    displayName: "Ordered Radio",
});
