import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class SwitchableViews extends BaseOptionComponent {
    static id = "switchable_views";
    static template = "website.SwitchableViews";
    static dependencies = ["switchableViews"];

    setup() {
        super.setup();
        const { getSwitchableRelatedViews } = this.dependencies.switchableViews;
        onWillStart(async () => {
            this.switchableRelatedViews = await getSwitchableRelatedViews();
        });
    }
}
registry.category("builder-options").add(SwitchableViews.id, SwitchableViews);
