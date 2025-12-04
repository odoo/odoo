import { BaseOptionComponent } from "@html_builder/core/utils";
import { useState } from "@odoo/owl";
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
