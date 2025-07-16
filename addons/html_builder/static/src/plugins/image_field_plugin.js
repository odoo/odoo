import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class ImageFieldPlugin extends Plugin {
    static id = "imageField";
    resources = {
        force_editable_selector: "[data-oe-field][data-oe-type=image] img",
        force_not_editable_selector: "[data-oe-field][data-oe-type=image]",
    };
}

registry.category("website-plugins").add(ImageFieldPlugin.id, ImageFieldPlugin);
