import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class MonetaryFieldPlugin extends Plugin {
    static id = "monetaryField";
    resources = {
        force_editable_selector: "[data-oe-field][data-oe-type=monetary] .oe_currency_value",
        force_not_editable_selector: "[data-oe-field][data-oe-type=monetary]",
    };
}

registry.category("website-plugins").add(MonetaryFieldPlugin.id, MonetaryFieldPlugin);
