import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class FooterCopyrightOption extends BaseOptionComponent {
    static template = "website.FooterCopyrightOption";
    static props = {
        getCurrentActiveViews: Function,
    };

    setup() {
        super.setup();
        this.languages = null;
        this.currentActiveViews = {};

        onWillStart(async () => {
            console.log(this.keys)
            this.languages = await rpc("/website/get_languages", {}, { cache: true });
            this.currentActiveViews = await this.props.getCurrentActiveViews(this.keys);
        });
    }

    hasSomeViews(views) {
        for (const view of views) {
            if (this.currentActiveViews[view]) {
                return true;
            }
        }
        return false;
    }
}
