import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class FloatingLabels extends Interaction {
    static selector = ".o_floating_labels";

    setup() {
        for (const controlEl of this.el.querySelectorAll(".form-control:not([placeholder])")) {
            controlEl.placeholder = " ";
            this.registerCleanup(() => controlEl.removeAttribute("placeholder"));
        }
    }
}

registry.category("public.interactions").add("web.floating_labels", FloatingLabels);
