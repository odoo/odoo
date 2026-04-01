import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class DateTimeFieldPlugin extends Plugin {
    static id = "dateTimeField";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        content_not_editable_selectors: [
            "[data-oe-field][data-oe-type=date]",
            "[data-oe-field][data-oe-type=datetime]",
        ],
    };
}
registry.category("builder-plugins").add(DateTimeFieldPlugin.id, DateTimeFieldPlugin);
