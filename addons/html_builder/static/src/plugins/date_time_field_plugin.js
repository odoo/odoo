import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class DateTimeFieldPlugin extends Plugin {
    static id = "dateTimeField";
    resources = {
        force_not_editable_selector: [
            "[data-oe-field][data-oe-type=date]",
            "[data-oe-field][data-oe-type=datetime]",
        ],
    };
}
registry.category("website-plugins").add(DateTimeFieldPlugin.id, DateTimeFieldPlugin);
