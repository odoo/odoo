import { BaseOptionComponent } from "@html_builder/core/utils";
import { useState } from "@odoo/owl";

export class TranslateWebpageOption extends BaseOptionComponent {
    static template = "website.TranslateWebpageOption";
    static props = {
        getTranslationState: Function,
    };

    setup() {
        super.setup();
        this.translationState = useState(this.props.getTranslationState());
    }
}
