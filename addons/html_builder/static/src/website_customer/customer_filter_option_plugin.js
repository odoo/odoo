import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CustomerFilterOptionPlugin extends Plugin {
    static id = "customerFilterOption";

    resources = {
        builder_options: {
            template: "website_customer.CustomerFilterOption",
            selector: ".o_wcrm_filters_top",
            groups: ["website.group_website_designer"],
            editableOnly: false,
        },
    };
}

registry.category("website-plugins").add(CustomerFilterOptionPlugin.id, CustomerFilterOptionPlugin);
