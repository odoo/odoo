import { Component, useRef } from "@odoo/owl";
import { WebsiteDialog } from "@website/components/dialog/dialog";

// Used to translate the text of `<select/>` options since it should not be
// possible to interact with the content of `.o_translation_select` elements.
export class SelectTranslateDialog extends Component {
    static components = { WebsiteDialog };
    static template = "website_builder.SelectTranslateDialog";
    static props = {
        node: {
            validate: (p) =>
                Array.isArray(p) && p.every(n => n.nodeType === Node.ELEMENT_NODE),
        },
        addStep: Function,
        close: Function,
    };
    setup() {
        this.inputEls = useRef("selectTranslateDialog");
    }

    onInputChange() {
        const inputs = this.inputEls.el.querySelectorAll(".select-translate-input");
        const values = Array.from(inputs).map(input => input.value);
        const options = this.optionEl;
        values.map((value, index) => [value, options[index]])
            .forEach(([value, option]) => {
                option.textContent = value;
                option.classList.toggle(
                    "oe_translated",
                    value !== option.dataset.initialTranslationValue
                );
            });
    }

    get optionEl() {
        return this.props.node;
    }

    addStepAndClose() {
        this.props.addStep();
        this.props.close();
    }
}
