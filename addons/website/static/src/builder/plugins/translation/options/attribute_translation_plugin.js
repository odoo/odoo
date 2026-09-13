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

export const translatableAttributesSelectors = [
    ".o_translatable_text",
    `.o_translatable_attribute:where(${TRANSLATABLE_ATTRIBUTES.map(
        (attr) => `[${attr.attribute}]`
    ).join(",")})`,
];

export class AttributeTranslationPlugin extends Plugin {
    static id = "attributeTranslation";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: { TranslateAttributeAction },
        builder_options_render_context: {
            translateAttributeOptionSelector: translatableAttributesSelectors.join(", "),
        },
    };
}

registry
    .category("translation-plugins")
    .add(AttributeTranslationPlugin.id, AttributeTranslationPlugin);

export class TranslateAttributeAction extends BuilderAction {
    static id = "translateAttribute";
    static dependencies = ["valueHistory"];

    isValueOfTextarea(el, attr) {
        return attr === "value" && el.tagName === "TEXTAREA";
    }

    getValue({ editingElement, params: { mainParam: attr } }) {
        return this.isValueOfTextarea(editingElement, attr)
            ? editingElement.value
            : editingElement.getAttribute(attr);
    }

    apply({ editingElement, params: { mainParam: attr }, value }) {
        if (attr === "value") {
            this.dependencies.valueHistory.setValue(editingElement, value);
        }
        if (!this.isValueOfTextarea(editingElement, attr)) {
            editingElement.setAttribute(attr, value);
        }
        editingElement.classList.add("oe_translated");
    }
}
