import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
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
                }),
            };
        });
    }
}

registry.category("website-options").add(TranslateAttributeOption.id, TranslateAttributeOption);
