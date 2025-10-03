import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import {
    TranslateAttributeOption,
    TranslateFormAttributeOption,
} from "./attribute_translation_option";

export class AttributeTranslationPlugin extends Plugin {
    static id = "attributeTranslation";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [TranslateAttributeOption, TranslateFormAttributeOption],
        builder_actions: { TranslateAttributeAction },
    };
}

registry
    .category("translation-plugins")
    .add(AttributeTranslationPlugin.id, AttributeTranslationPlugin);

export class TranslateAttributeAction extends BuilderAction {
    static id = "translateAttribute";
    static dependencies = ["history", "translation"];

    getValue({ editingElement, params: { mainParam: attr } }) {
        if (attr === "value" && editingElement.tagName === "TEXTAREA") {
            return editingElement.value;
        }
        return editingElement.getAttribute(attr);
    }

    apply({ editingElement, params: { mainParam: attr }, value }) {
        const isTextarea = editingElement.tagName === "TEXTAREA";
        const oldValue =
            attr === "value" ? editingElement.value : editingElement.getAttribute(attr);
        editingElement.setAttribute(attr, value);
        editingElement.classList.add("oe_translated");

        const setCustomHistory = (value) => {
            if (attr === "value") {
                editingElement.value = value;
                if (isTextarea) {
                    this.dependencies.translation.updateTranslationMap(
                        editingElement,
                        value,
                        "textContent"
                    );
                    return;
                }
            }
            this.dependencies.translation.updateTranslationMap(editingElement, value, attr);
        };

        this.dependencies.history.applyCustomMutation({
            apply: () => {
                setCustomHistory(value);
            },
            revert: () => {
                setCustomHistory(oldValue);
            },
        });
    }
}
