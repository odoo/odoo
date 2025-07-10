import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class FooterCopyrightOption extends BaseOptionComponent {
    static template = "website.FooterCopyrightOption";
    static props = {};

    setup() {
        super.setup();
        this.languages = null;

        onWillStart(async () => {
            this.languages = await rpc("/website/get_languages", {}, { cache: true });
        });
    }
}
