import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class ImageFieldPlugin extends Plugin {
    static id = "imageField";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        content_editable_selectors: "[data-oe-field][data-oe-type=image] img",
        content_not_editable_selectors: "[data-oe-field][data-oe-type=image]",
    };
}

registry.category("builder-plugins").add(ImageFieldPlugin.id, ImageFieldPlugin);
