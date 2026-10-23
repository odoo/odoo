import { BuilderAction } from "@html_builder/core/builder_action";
import { altTranslations, titleTranslations } from "@html_builder/plugins/image/image_tool_option";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const TRANSLATABLE_ATTRIBUTES = [
    {
        attribute: "alt",
        name: _t("Description"),
        ...altTranslations,
    },
    {
        attribute: "title",
        name: _t("Tooltip"),
        ...titleTranslations,
    },
    {
        attribute: "placeholder",
        name: _t("Placeholder"),
    },
    {
        attribute: "aria-label",
        name: _t("Description"),
        tooltip: _t("'Aria label' adds context for people using screen readers."),
        placeholder: _t("Aria label"),
    },
    {
        attribute: "value",
        name: _t("Value"),
    },
    {
        // This is a "fake attribute": it is present in the translation info
        // from the translation plugin, but it corresponds to the `textContent`
        // property of the element (not an attribute)
        attribute: "textContent",
        name: _t("Value"),
    },
];

const translatableAttributesSelector = TRANSLATABLE_ATTRIBUTES.map(({ attribute }) =>
    attribute === "textContent" ? ".o_translatable_text" : `.o_translatable_attribute[${attribute}]`
).join(",");

export class AttributeTranslationPlugin extends Plugin {
    static id = "attributeTranslation";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: { TranslateAttributeAction },
        builder_options_render_context: {
            translateAttributeOptionSelector: translatableAttributesSelector,
        },
    };
}

registry
    .category("translation-plugins")
    .add(AttributeTranslationPlugin.id, AttributeTranslationPlugin);

export class TranslateAttributeAction extends BuilderAction {
    static id = "translateAttribute";
    static dependencies = ["valueHistory"];

    getValue({ editingElement, params: { mainParam: attr } }) {
        return attr === "textContent"
            ? editingElement.textContent
            : editingElement.getAttribute(attr);
    }

    apply({ editingElement, params: { mainParam: attr }, value }) {
        if (attr === "textContent") {
            editingElement.textContent = value;
        } else {
            editingElement.setAttribute(attr, value);
        }
        if (attr === "textContent" || attr === "value") {
            this.dependencies.valueHistory.setValue(editingElement, value);
        }
    }
}
