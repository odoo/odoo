import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class FloatingLabels extends Interaction {
    static selector = ".o_floating_labels";

    setup() {
        for (const inputEl of this.el.querySelectorAll("input.form-control:not([placeholder])")) {
            inputEl.placeholder = " ";
        }
    }
}

registry.category("public.interactions").add("website.floating_labels", FloatingLabels);
