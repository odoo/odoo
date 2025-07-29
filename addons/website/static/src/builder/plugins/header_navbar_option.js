import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";

export class HeaderNavbarOption extends BaseOptionComponent {
    static template = "website.HeaderNavbarOption";
    static props = {
        getCurrentActiveViews: Function,
    };
    static selector = "#wrapwrap > header";
    static editableOnly = false;
    static groups = ["website.group_website_designer"];
    static reloadTarget = true;

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
