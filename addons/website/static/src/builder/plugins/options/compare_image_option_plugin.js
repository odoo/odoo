import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CompareImageOptionPlugin extends Plugin {
    static id = "compareImageOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        so_content_addition_selectors: [".s_compare_image"],
    };
}

registry.category("builder-plugins").add(CompareImageOptionPlugin.id, CompareImageOptionPlugin);
