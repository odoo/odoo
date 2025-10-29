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
<<<<<<< 189f0506f09249c5a7c2f7b7a5b02d9bd996014d
||||||| 4a1299e5439fa44eb73d613fec843f06dabaf895
Object.assign(HeaderNavigationOption, basicHeaderOptionSettings);
=======

Object.assign(HeaderNavigationOption, basicHeaderOptionSettings);
>>>>>>> 2bf23d432e9f7e85c8be1c9b1630f6a133c956c8
