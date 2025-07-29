import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { HeaderNavbarOption } from "./header_navbar_option";

class HeaderNavbarOptionPlugin extends Plugin {
    static id = "HeaderNavbarOptionPlugin";
    static dependencies = ["customizeWebsite"];

    resources = {
        builder_options: [HeaderNavbarOption],
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
}

registry.category("website-plugins").add(HeaderNavbarOptionPlugin.id, HeaderNavbarOptionPlugin);
