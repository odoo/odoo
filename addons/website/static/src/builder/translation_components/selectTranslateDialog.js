import { Component, useRef } from "@odoo/owl";
import { WebsiteDialog } from "@website/components/dialog/dialog";

// Used to translate the text of `<select/>` options since it should not be
// possible to interact with the content of `.o_translation_select` elements.
export class SelectTranslateDialog extends Component {
    static components = { WebsiteDialog };
    static template = "website_builder.SelectTranslateDialog";
    static props = {
        node: { validate: (p) => p.nodeType === Node.ELEMENT_NODE },
        addStep: Function,
        close: Function,
    };
    setup() {
        this.inputEl = useRef("translateInputs");
    }

    onInputChange(el) {
        const inputEls = Array.from(this.inputEl.el.querySelectorAll("input"));
        const index = inputEls.findIndex(input => input.isSameNode(el.target));
        const value = el.target.value;
        const optionEl = this.optionEls[index];

        if (optionEl) {
            optionEl.textContent = value;
            optionEl.classList.toggle(
                "oe_translated",
                value !== optionEl.dataset.initialTranslationValue
            );
        }
    }

    get optionEls() {
        return this.props.node.querySelectorAll(".o_translation_select_option");
    }

    addStepAndClose() {
        this.props.addStep();
        this.props.close();
    }
}
