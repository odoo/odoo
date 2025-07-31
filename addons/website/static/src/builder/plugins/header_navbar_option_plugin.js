import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { HeaderNavbarOption } from "./header_navbar_option";

class HeaderNavbarOptionPlugin extends Plugin {
    static id = "HeaderNavbarOptionPlugin";
    static dependencies = ["customizeWebsite"];
    static shared = ["getCurrentActiveViews"];

    resources = {
        builder_options: [
            {
                props: {
                    getCurrentActiveViews: () => this.getCurrentActiveViews.bind(this.keys),
                },
                OptionComponent: HeaderNavbarOption,
                editableOnly: false,
                selector: "#wrapwrap > header",
                groups: ["website.group_website_designer"],
                reloadTarget: true,
            },
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
    async getCurrentActiveViews(keys) {
        const actionParams = { views: keys };
        await this.dependencies.customizeWebsite.loadConfigKey(actionParams);
        const currentActiveViews = {};
        for (const key of keys) {
            const isActive = this.dependencies.customizeWebsite.getConfigKey(key);
            currentActiveViews[key] = isActive;
        }
        return currentActiveViews;
    }
}
registry.category("website-plugins").add(HeaderNavbarOptionPlugin.id, HeaderNavbarOptionPlugin);
