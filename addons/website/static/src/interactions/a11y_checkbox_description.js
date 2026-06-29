import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class A11yCheckboxDescription extends Interaction {
    static selector =
        ".s_website_form_field:has(.form-check):has(.s_website_form_label.d-none, .s_website_form_label.invisible)";

    dynamicContent = {
        ".s_website_form_field_description": {
            "t-on-click": () => {
                this.inputEl.checked = !this.inputEl.checked;
            },
        },
    };

    setup() {
        this.inputEl = this.el.querySelector("input[type='checkbox']");
    }
}

registry
    .category("public.interactions")
    .add("website.a11y_checkbox_description", A11yCheckboxDescription);
