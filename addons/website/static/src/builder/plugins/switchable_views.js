import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";

export class SwitchableViews extends BaseOptionComponent {
    static template = "website.SwitchableViews";
    static props = {
        getSwitchableRelatedViews: Function,
    };

    setup() {
        super.setup();
        onWillStart(async () => {
            this.switchableRelatedViews = await this.props.getSwitchableRelatedViews();
        });
    }
}
