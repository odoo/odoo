import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { Multirange } from "@website/../lib/multirange/multirange_custom";

export class RangeFilter extends Interaction {
    static selector = ".o_attr_range[multiple]";

    setup() {
        const input = this.el;
        const values = JSON.parse(input.dataset.values || "[]");

        if (!values.length) {
            return;
        }

        const instance = new Multirange(input);
        // Override to show attribute names instead of numbers
        instance.counterInputUpdate = () => {
            const minIdx = Math.round(instance.input.valueLow);
            const maxIdx = Math.round(instance.input.valueHigh);
            instance.leftCounter.textContent = values[minIdx] ?? "";
            instance.rightCounter.textContent = values[maxIdx] ?? "";
        };

        instance.update();
    }
}

registry.category("public.interactions").add("website_sale.range_filter", RangeFilter);
