import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadLanguages } from "@web/core/l10n/translation";

export class TranslateWebpageOption extends BaseOptionComponent {
    static template = "website.TranslateWebpageOption";
    static props = {};

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({
            languages: [],
        });
        onWillStart(() => {
            loadLanguages(this.orm).then((res) => {
                this.state.languages = res;
            });
        });
    }
}
