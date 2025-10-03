import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const TRANSLATABLE_ATTRIBUTES = [
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

const translatableAttributesSelectors = [
    ".o_translatable_text",
    `.o_translatable_attribute:where(${TRANSLATABLE_ATTRIBUTES.map(
        (attr) => `[${attr.attribute}]`
    ).join(",")})`,
];

export class AttributeTranslationPlugin extends Plugin {
    static id = "attributeTranslation";
    static dependencies = ["translation"];

    resources = {
        builder_options: [
            {
                OptionComponent: TranslateAttributeOption,
                selector: translatableAttributesSelectors.join(", "),
                exclude: translatableAttributesSelectors
                    .map((sel) => `.s_website_form_field ${sel}`)
                    .join(", "),
                isTranslationOption: true,
                props: {
                    getTranslationInfo: this.dependencies.translation.getTranslationInfo,
                },
            },
            {
                OptionComponent: TranslateAttributeOption,
                selector: ".s_website_form_field",
                exclude: ".s_website_form_dnone",
                applyTo: translatableAttributesSelectors.join(", "),
                isTranslationOption: true,
                props: {
                    getTranslationInfo: this.dependencies.translation.getTranslationInfo,
                },
            },
        ],
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

export class TranslateAttributeOption extends BaseOptionComponent {
    static template = "website.TranslateAttributeOption";
    static props = {
        getTranslationInfo: { Function },
    };

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const elTranslationInfo = this.props.getTranslationInfo(editingElement);
            return {
                availableAttributes: TRANSLATABLE_ATTRIBUTES.filter((attr) => {
                    if (attr.attribute === "value" && editingElement.tagName === "TEXTAREA") {
                        return !!elTranslationInfo.textContent;
                    }
                    return (
                        editingElement.hasAttribute(attr.attribute) &&
                        !!elTranslationInfo[attr.attribute]
                    );
                }),
            };
        });
    }
}
