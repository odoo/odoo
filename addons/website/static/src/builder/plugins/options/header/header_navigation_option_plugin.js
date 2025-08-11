import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { HeaderNavigationOption } from "./header_navigation_option";
import { HEADER_NAVIGATION, basicHeaderOptionSettings } from "./header_option_plugin";
import { withSequence } from "@html_editor/utils/resource";

class HeaderNavigationOptionPlugin extends Plugin {
    static id = "HeaderNavigationOptionPlugin";
    static dependencies = ["customizeWebsite"];

    resources = {
        builder_options: [
            withSequence(HEADER_NAVIGATION, {
                ...basicHeaderOptionSettings,
                OptionComponent: HeaderNavigationOption,
                props: {
                    getCurrentActiveViews: this.getCurrentActiveViews.bind(this),
                },
                reloadTarget: true,
            }),
        ],
    };

    setup() {
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

registry
    .category("website-plugins")
    .add(HeaderNavigationOptionPlugin.id, HeaderNavigationOptionPlugin);
