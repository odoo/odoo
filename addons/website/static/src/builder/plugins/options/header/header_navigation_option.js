import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { basicHeaderOptionSettings } from "./basicHeaderOptionSettings";

export class HeaderNavigationOption extends BaseOptionComponent {
    static template = "website.HeaderNavigationOption";
    static dependencies = ["customizeWebsite"];
    static reloadTarget = true;

    setup() {
        super.setup();

        this.keys = [
            "website.template_header_default",
            "website.template_header_hamburger",
            "website.template_header_boxed",
            "website.template_header_stretch",
            "website.template_header_vertical",
            "website.template_header_search",
            "website.template_header_sales_one",
            "website.template_header_sales_two",
            "website.template_header_sales_three",
            "website.template_header_sales_four",
            "website.template_header_sidebar",
        ];

        this.currentActiveViews = {};
        onWillStart(async () => {
            this.currentActiveViews = await this.getCurrentActiveViews();
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
    async getCurrentActiveViews() {
        const actionParams = { views: this.keys };
        await this.dependencies.customizeWebsite.loadConfigKey(actionParams);
        const currentActiveViews = {};
        for (const key of this.keys) {
            const isActive = this.dependencies.customizeWebsite.getConfigKey(key);
            currentActiveViews[key] = isActive;
        }
        return currentActiveViews;
    }
}

Object.assign(HeaderNavigationOption, basicHeaderOptionSettings);
