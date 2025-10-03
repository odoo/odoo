import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";

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

export class TranslateAttributeOption extends BaseOptionComponent {
    static template = "website.TranslateAttributeOption";
    static selector = translatableAttributesSelectors.join(", ");
    static exclude = translatableAttributesSelectors
        .map((sel) => `.s_website_form_field ${sel}`)
        .join(", ");
    static editableOnly = false;
    static dependencies = ["translation"];

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const elTranslationInfo =
                this.dependencies.translation.getTranslationInfo(editingElement);
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

export class TranslateFormAttributeOption extends TranslateAttributeOption {
    static selector = ".s_website_form_field";
    static exclude = ".s_website_form_dnone";
    static applyTo = translatableAttributesSelectors.join(", ");
    static editableOnly = false;
}
