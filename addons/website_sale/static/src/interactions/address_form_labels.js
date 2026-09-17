import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class AddressFormLabels extends Interaction {
    static selector = "#o_wsale_address_form.o_floating_labels";

    setup() {
        for (const iconEl of this.el.querySelectorAll(".col-form-label + .oi")) {
            iconEl.previousElementSibling.append(iconEl);
        }
    }
}

registry.category("public.interactions").add("website_sale.address_form_labels", AddressFormLabels);
