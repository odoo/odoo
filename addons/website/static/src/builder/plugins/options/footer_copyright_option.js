import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class FooterCopyrightOption extends BaseOptionComponent {
    static id = "footer_copyright_option";
    static template = "website.FooterCopyrightOption";

    setup() {
        super.setup();
        this.languages = null;

        onWillStart(async () => {
            this.languages = await rpc("/website/get_languages", {}, { cache: true });
        });
    }
}

registry.category("website-options").add(FooterCopyrightOption.id, FooterCopyrightOption);
