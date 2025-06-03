import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CustomerFilterOption } from "./customer_filter_option";

export class CustomerFilterOptionPlugin extends Plugin {
    static id = "customerFilterOption";

    resources = {
        builder_options: {
            OptionComponent: CustomerFilterOption,
            selector: "main:not(:has(#oe_structure_website_crm_partner_assign_layout_1)):has(.o_wcrm_filters_top)",
            title: _t("Customers Page"),
            groups: ["website.group_website_designer"],
            editableOnly: false,
        },
    };
}

registry.category("website-plugins").add(CustomerFilterOptionPlugin.id, CustomerFilterOptionPlugin);
