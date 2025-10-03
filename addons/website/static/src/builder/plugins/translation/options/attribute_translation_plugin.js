import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const TRANSLATABLE_ATTRIBUTES = [
    {
        attribute: "alt",
        name: _t("Description"),
        tooltip: _t(
            "'Alt tag' specifies an alternate text for an image, if the image cannot be displayed (slow connection, missing image, screen reader ...)."
        ),
        placeholder: _t("Alt tag"),
    },
    {
        attribute: "title",
        name: _t("Tooltip"),
        tooltip: _t("'Title tag' is shown as a tooltip when you hover the picture."),
        placeholder: _t("Title tag"),
    },
    {
        attribute: "placeholder",
        name: _t("Placeholder"),
    },
    {
        attribute: "value",
        name: _t("Value"),
    },
];

export class AttributeTranslationPlugin extends Plugin {
    static id = "attributeTranslation";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: { TranslateAttributeAction },
        builder_options_render_context: {
            translateAttributeOptionSelector: ".o_translatable_text, .o_translatable_attribute",
        },
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
        if (!isTextarea || attr !== "value") {
            editingElement.setAttribute(attr, value);
        }
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
