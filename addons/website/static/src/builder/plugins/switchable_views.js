import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";

export class SwitchableViews extends BaseOptionComponent {
    static template = "website.SwitchableViews";
    static dependencies = ["switchableViews"];
    static selector = ".o_portal_wrap";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;

    setup() {
        super.setup();
        const { getSwitchableRelatedViews } = this.dependencies.switchableViews;
        onWillStart(async () => {
            this.switchableRelatedViews = await getSwitchableRelatedViews();
        });
    }
}
