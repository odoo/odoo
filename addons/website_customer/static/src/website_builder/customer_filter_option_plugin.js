import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { CustomerFilterOption } from "./customer_filter_option";

export class CustomerFilterOptionPlugin extends Plugin {
    static id = "customerFilterOption";

    resources = {
        builder_options: CustomerFilterOption,
    };
}

registry.category("website-plugins").add(CustomerFilterOptionPlugin.id, CustomerFilterOptionPlugin);
