import { BaseOptionComponent } from "@html_builder/core/utils";
import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class TranslateWebpageOption extends BaseOptionComponent {
    static template = "website.TranslateWebpageOption";
    static selector = "body";
    static title = _t("Translation");
    static hideOverlay = true;
    static editableOnly = false;

    setup() {
        super.setup();
        this.translationState = useState(
            this.env.editor.shared.translateWebpageOption.getTranslationState()
        );
    }
}
