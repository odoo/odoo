import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class A11yCheckboxDescription extends Interaction {
    static selector = ".s_website_form_field";
    static selectorHas = ".form-check";

    start() {
        const descriptionEl = this.el.querySelector(".s_website_form_field_description");
        this.addListener(descriptionEl, "click", (event) => {
            if (!this._isLabelHidden()) {
                return;
            }
            if (["A", "BUTTON"].includes(event.target.tagName)) {
                return;
            }
            const inputEl = event.currentTarget
                .closest(".s_website_form_field")
                .querySelector(".s_website_form_input");
            inputEl.checked = !inputEl.checked;
        });
    }

    _isLabelHidden() {
        return (
            this.el.querySelector(
                ".s_website_form_label.invisible, .s_website_form_label.d-none"
            ) !== null
        );
    }
}

registry
    .category("public.interactions")
    .add("website.a11y_checkbox_description", A11yCheckboxDescription);
