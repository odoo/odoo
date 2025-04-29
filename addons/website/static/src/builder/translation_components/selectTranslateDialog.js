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
        this.inputEl = useRef("input");
    }

    onInputChange() {
        const value = this.inputEl.el.value;
        this.optionEl.textContent = value;
        this.optionEl.classList.toggle(
            "oe_translated",
            value !== this.optionEl.dataset.initialTranslationValue
        );
    }

    get optionEl() {
        return this.props.node;
    }

    addStepAndClose() {
        this.props.addStep();
        this.props.close();
    }
}
