import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { TRANSLATABLE_ATTRIBUTES } from "@website/builder/plugins/translation/options/attribute_translation_plugin";

export class TranslateAttributeOption extends BaseOptionComponent {
    static id = "translate_attribute_option";
    static template = "website.TranslateAttributeOption";
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
                    return !!elTranslationInfo[attr.attribute];
                }).map((attr) => this.getAttributeLabel(editingElement, attr)),
            };
        });
    }

    getAttributeLabel(editingElement, attr) {
        if (attr.attribute === "title" && editingElement.matches(".media_iframe_video")) {
            return {
                ...attr,
                name: _t("Description"),
                tooltip: _t(
                    "Helps screen readers and improves SEO by providing a relevant description."
                ),
                placeholder: _t("Describe content"),
            };
        }
        return attr;
    }
}

registry.category("website-options").add(TranslateAttributeOption.id, TranslateAttributeOption);
