import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

class MasonryItemOptionPlugin extends Plugin {
    static id = "masonryItemOption";
    resources = {
        builder_options: [
            withSequence(15, {
                template: "html_builder.MasonryItemOption",
                selector: ".s_masonry_block .o_grid_item",
                exclude: ".o_grid_item_image",
            }),
        ],
    };
}

registry.category("website-plugins").add(MasonryItemOptionPlugin.id, MasonryItemOptionPlugin);
