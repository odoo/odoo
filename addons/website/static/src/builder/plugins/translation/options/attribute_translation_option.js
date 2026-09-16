import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { TRANSLATABLE_ATTRIBUTES } from "@website/builder/plugins/translation/options/attribute_translation_plugin";

const VIDEO_DESCRIPTION_ATTRIBUTE = {
    attribute: "title",
    name: _t("Description"),
    tooltip: _t("Helps screen readers and improves SEO by providing a relevant description."),
    placeholder: _t("Describe content"),
};

export class TranslateAttributeOption extends BaseOptionComponent {
    static id = "translate_attribute_option";
    static template = "website.TranslateAttributeOption";
    static dependencies = ["translation"];

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const elTranslationInfo =
                this.dependencies.translation.getTranslationInfo(editingElement);
            const isVideo = editingElement.matches(".media_iframe_video");
            return {
                availableAttributes: TRANSLATABLE_ATTRIBUTES.filter((attr) => {
                    if (attr.attribute === "value" && editingElement.tagName === "TEXTAREA") {
                        return !!elTranslationInfo.textContent;
                    }
                    return !!elTranslationInfo[attr.attribute];
                }).map((attr) =>
                    isVideo && attr.attribute === "title" ? VIDEO_DESCRIPTION_ATTRIBUTE : attr
                ),
            };
        });
    }
}

registry.category("website-options").add(TranslateAttributeOption.id, TranslateAttributeOption);
