import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CompareImageOptionPlugin extends Plugin {
    static id = "compareImageOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        so_content_addition_selectors: [".s_compare_image"],
        // Images can only be replaced by images, as the snippet compares two
        // images.
        replace_media_dialog_params_processors: (params) => {
            if (params.node.matches(".s_compare_image_frame img")) {
                params.onlyImages = true;
            }
            return params;
        },
    };
}

registry.category("website-plugins").add(CompareImageOptionPlugin.id, CompareImageOptionPlugin);
