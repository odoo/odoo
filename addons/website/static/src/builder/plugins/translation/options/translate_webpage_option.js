import { useState } from "@web/owl2/utils";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";

export class TranslateWebpageOption extends BaseOptionComponent {
    static id = "translate_webpage_option";
    static template = "website.TranslateWebpageOption";
    static hideOverlay = true;

    setup() {
        super.setup();
        this.translationState = useState(
            this.env.editor.shared.translateWebpageOption.getTranslationState()
        );
    }
}

registry.category("website-options").add(TranslateWebpageOption.id, TranslateWebpageOption);
