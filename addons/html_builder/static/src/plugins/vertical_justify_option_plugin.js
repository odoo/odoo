import { END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BaseOptionComponent } from "@html_builder/core/utils";

class VerticalJustifyOptionPlugin extends Plugin {
    static id = "verticalJustifyOption";
    resources = {
        builder_options: [withSequence(END, VerticalJustifyOption)],
    };
}

export class VerticalJustifyOption extends BaseOptionComponent {
    static template = "html_builder.VerticalJustifyOption";
    static selector =
        ".s_masonry_block .o_grid_item, .s_quadrant .o_grid_item, .s_banner_categories .o_grid_item";
    static exclude = ".o_grid_item_image";
}

registry
    .category("builder-plugins")
    .add(VerticalJustifyOptionPlugin.id, VerticalJustifyOptionPlugin);
