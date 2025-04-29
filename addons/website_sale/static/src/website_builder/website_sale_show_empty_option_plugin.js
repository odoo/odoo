import { HEADER_END } from "@website/builder/plugins/options/header_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class WebsiteSaleShowEmptyOptionPlugin extends Plugin {
    static id = "showEmptyOption";
    resources = {
        builder_options: [
            withSequence(HEADER_END, {
                template: "website_sale.ShowEmptyOption",
                selector: "#wrapwrap > header",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteSaleShowEmptyOptionPlugin.id, WebsiteSaleShowEmptyOptionPlugin);
