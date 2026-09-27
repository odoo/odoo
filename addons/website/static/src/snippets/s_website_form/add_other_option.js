import { registry } from "@web/core/registry";
import { generateHTMLId } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";
import { Interaction } from "@web/public/interaction";

export class AddOtherOption extends Interaction {
    static selector = "[data-other-option-allowed]";
    dynamicContent = {
        ".form-select, .s_website_form_multiple": {
            "t-on-change": this.onChangeSelectOrRadio,
        },
        ".o_other_input": {
            "t-att-class": () => ({ "d-none": !this.isOtherSelected }),
            "t-att-required": () => this.isOtherSelected,
        },
    };

    setup() {
        this.selectOrRadioEl = this.el.querySelector(".form-select, .s_website_form_multiple");
        this.isOtherSelected = false;
    }

    start() {
        if (!this.selectOrRadioEl) {
            return;
        }
        this.createOtherOption();
        this.createOtherInput();
        // Refresh the `dynamicContent` to ensure `dynamicContent` related to
        // newly inserted nodes are applied
        this.updateContent();
    }

    /**
     * Creates and inserts the "Other" option for select/radio fields.
     */
    createOtherOption() {
        const otherId = generateHTMLId();
        const otherLabel = this.el.dataset.otherOptionLabel || _t("Other");
        let otherOptionEl;

        if (this.selectOrRadioEl.tagName === "SELECT") {
            // Create dropdown option element
            otherOptionEl = new Option(otherLabel, "_other");
        } else {
            //  Clone last radio button to preserve styling, then update its
            //  attributes
            otherOptionEl = this.selectOrRadioEl.lastElementChild.cloneNode(true);

            const inputEl = otherOptionEl.querySelector("input");
            inputEl.removeAttribute("checked");
            inputEl.id = otherId;
            inputEl.value = "_other";

            const labelEl = otherOptionEl.querySelector("label");
            labelEl.htmlFor = otherId;
            labelEl.textContent = otherLabel;
        }

        // Append the "Other" option to the field
        this.insert(otherOptionEl, this.selectOrRadioEl, "beforeend");
    }

    /**
     * Creates and inserts a hidden text input field that will be shown
     * when the "Other" option is selected.
     */
    createOtherInput() {
        const otherInputEl = Object.assign(document.createElement("input"), {
            type: "text",
            name: this.selectOrRadioEl.name || this.selectOrRadioEl.dataset.name,
            placeholder: this.el.dataset.otherOptionPlaceholder || "",
            className: "form-control s_website_form_input o_other_input mt-3",
        });
        this.insert(otherInputEl, this.selectOrRadioEl, "afterend");
    }

    /**
     * Handle change events on select dropdowns or radio button groups.
     *
     * Shows/hides the custom "Other" input field based on whether "_other" is
     * selected. The input becomes required when visible and optional when
     * hidden.
     *
     * @param {Event} ev
     */
    onChangeSelectOrRadio(ev) {
        const targetEl = ev.currentTarget;

        // Get selected value based on element type
        const selectedValue =
            targetEl.tagName === "SELECT"
                ? targetEl.value
                : targetEl.querySelector("input[type='radio']:checked").value;

        this.isOtherSelected = selectedValue === "_other";
    }
}

registry.category("public.interactions").add("website.form.add_other_option", AddOtherOption);
