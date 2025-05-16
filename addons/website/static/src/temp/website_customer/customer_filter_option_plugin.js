import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { CustomerFilterOption } from "./customer_filter_option";

export class CustomerFilterOptionPlugin extends Plugin {
    static id = "customerFilterOption";

    resources = {
        builder_options: {
            OptionComponent: CustomerFilterOption,
            selector: ".o_wcrm_filters_top",
            groups: ["website.group_website_designer"],
            editableOnly: false,
        },
    };
}

registry.category("website-plugins").add(CustomerFilterOptionPlugin.id, CustomerFilterOptionPlugin);
