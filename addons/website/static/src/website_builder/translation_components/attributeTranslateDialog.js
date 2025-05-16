import { Component } from "@odoo/owl";
import { WebsiteDialog } from "@website/components/dialog/dialog";

export class AttributeTranslateDialog extends Component {
    static components = { WebsiteDialog };
    static template = "website_builder.AttributeTranslateDialog";
    static props = {
        node: { validate: (p) => p.nodeType === Node.ELEMENT_NODE },
        elToTranslationInfoMap: Object,
        addStep: Function,
        applyCustomMutation: Function,
        close: Function,
    };

    setup() {
        this.modifiedAttrs = {};
    }

    onInputChange(ev) {
        const inputEl = ev.target;
        const attr = inputEl.previousSibling.textContent;
        const translateEl = this.props.node;
        const newValue = inputEl.value;
        this.modifiedAttrs[attr] = newValue;
        if (attr !== "textContent") {
            translateEl.setAttribute(attr, newValue);
            if (attr === "value") {
                translateEl.value = newValue;
            }
        } else {
            translateEl.value = newValue;
        }
        translateEl.classList.add("oe_translated");
    }

    get translationInfos() {
        return this.props.elToTranslationInfoMap.get(this.props.node);
    }

    addStepAndClose() {
        const oldValue = JSON.parse(JSON.stringify(this.translationInfos));
        this.props.applyCustomMutation({
            apply: () => {
                for (const [attr, newValue] of Object.entries(this.modifiedAttrs)) {
                    this.translationInfos[attr].translation = newValue;
                }
            },
            revert: () => {
                for (const attr of Object.keys(this.modifiedAttrs)) {
                    this.translationInfos[attr].translation = oldValue[attr].translation;
                }
            },
        });
        this.props.addStep();
        this.props.close();
    }
}
