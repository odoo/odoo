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
        this.translateEl = useRef("translateInputs");
    }

    onInputChange(ev) {
        const index = ev.target.dataset.index;
        const value = ev.target.value;
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
