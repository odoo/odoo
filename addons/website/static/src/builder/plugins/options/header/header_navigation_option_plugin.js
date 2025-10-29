import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { HeaderNavigationOption } from "./header_navigation_option";
<<<<<<< 189f0506f09249c5a7c2f7b7a5b02d9bd996014d
import { HEADER_NAVIGATION, basicHeaderOptionSettings } from "./header_option_plugin";
import { withSequence } from "@html_editor/utils/resource";
||||||| 4a1299e5439fa44eb73d613fec843f06dabaf895
=======
import { withSequence } from "@html_editor/utils/resource";
import { HEADER_NAVIGATION } from "./header_option_plugin";
>>>>>>> 2bf23d432e9f7e85c8be1c9b1630f6a133c956c8

class HeaderNavigationOptionPlugin extends Plugin {
    static id = "HeaderNavigationOptionPlugin";
    static dependencies = ["customizeWebsite"];

    resources = {
<<<<<<< 189f0506f09249c5a7c2f7b7a5b02d9bd996014d
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
||||||| 4a1299e5439fa44eb73d613fec843f06dabaf895
        builder_options: [HeaderNavigationOption],
=======
        builder_options: [withSequence(HEADER_NAVIGATION, HeaderNavigationOption)],
>>>>>>> 2bf23d432e9f7e85c8be1c9b1630f6a133c956c8
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
