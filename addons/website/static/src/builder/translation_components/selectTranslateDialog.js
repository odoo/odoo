import { Component } from "@odoo/owl";
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
        this.modifiedOptions = {};
    }

    onInputChange(ev) {
        const index = ev.target.dataset.index;
        const value = ev.target.value;
        this.modifiedOptions[index] = value;
    }

    get optionEls() {
        return this.props.node.querySelectorAll(".o_translation_select_option");
    }

    addStepAndClose() {
        for (const [index, newValue] of Object.entries(this.modifiedOptions)) {
            const optionEl = this.optionEls[index];
            optionEl.textContent = newValue;
            optionEl.classList.add("oe_translated");
        }
        this.props.addStep();
        this.props.close();
    }
}
