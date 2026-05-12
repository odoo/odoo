import { Component, useRef } from "@odoo/owl";
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
        this.container = useRef("container");
    }

    // TODO: remove in master
    onInputChange() {}

    updateAttributes() {
        for (const [attr, oldValue] of Object.entries(this.translationInfos)) {
            const translateEl = this.props.node;
            const inputEl = this.container.el.querySelector(`input.${attr}-translation`);
            const newValue = inputEl.value;
            if (newValue === oldValue.translation) {
                continue;
            }
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
    }

    get translationInfos() {
        return this.props.elToTranslationInfoMap.get(this.props.node);
    }

    addStepAndClose() {
        this.updateAttributes();
        // If there are no modifiedAttrs, just close the dialog.
        if (!Object.keys(this.modifiedAttrs).length) {
            this.props.close();
            return;
        }
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
