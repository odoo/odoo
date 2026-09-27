import { proxy } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";

export class TranslateWebpageOption extends BaseOptionComponent {
    static id = "translate_webpage_option";
    static template = "website.TranslateWebpageOption";
    static hideOverlay = true;

    setup() {
        super.setup();
        this.translationState = proxy(
            this.env.editor.shared.translateWebpageOption.getTranslationState()
        );
    }
}

registry.category("website-options").add(TranslateWebpageOption.id, TranslateWebpageOption);
