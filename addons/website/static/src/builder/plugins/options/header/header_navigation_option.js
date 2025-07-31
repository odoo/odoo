import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";

export class HeaderNavigationOption extends BaseOptionComponent {
    static template = "website.HeaderNavigationOption";
    static props = {
        getCurrentActiveViews: Function,
    };
    setup() {
        super.setup();
        this.currentActiveViews = {};
        onWillStart(async () => {
            this.currentActiveViews = await this.props.getCurrentActiveViews();
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
