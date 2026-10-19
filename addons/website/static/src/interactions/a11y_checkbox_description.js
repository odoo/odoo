import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { generateHTMLId } from "@web/core/utils/strings";

export class A11yCheckboxDescription extends Interaction {
    static selector = ".s_website_form_field";
    static selectorHas = [
        ".form-check",
        ".s_website_form_label.d-none, .s_website_form_label.invisible",
    ];

    dynamicContent = {
        ".s_website_form_field_description": {
            "t-on-click": (ev) => {
                if (!this.isWithinLink(ev.target)) {
                    this.inputEl.checked = !this.inputEl.checked;
                }
            },
            "t-att-id": () => this.id,
        },
        "input[type='checkbox']": {
            "t-att-aria-labelledby": () => this.id,
        },
    };

    setup() {
        this.inputEl = this.el.querySelector("input[type='checkbox']");
        this.id = generateHTMLId();
    }

    isWithinLink(el) {
        return !!el.closest("a");
    }
}

registry
    .category("public.interactions")
    .add("website.a11y_checkbox_description", A11yCheckboxDescription);
