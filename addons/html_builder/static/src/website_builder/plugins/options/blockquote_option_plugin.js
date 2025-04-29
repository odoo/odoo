import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { WebsiteBackgroundOption } from "@html_builder/website_builder/plugins/options/background_option";

class BlockquoteOptionPlugin extends Plugin {
    static id = "blockquoteOption";
    selector = ".s_blockquote";
    resources = {
        mark_color_level_selector_params: [{ selector: this.selector }],
        builder_options: [
            withSequence(30, {
                selector: this.selector,
                OptionComponent: WebsiteBackgroundOption,
                props: {
                    withColors: true,
                    withImages: true,
                    withShapes: true,
                    withColorCombinations: true,
                },
            }),
            withSequence(40, {
                template: "website.BlockquoteOption",
                selector: this.selector,
            }),
        ],
    };
}
// TODO: as in master, the position of a background image does not work
// correctly.
registry.category("website-plugins").add(BlockquoteOptionPlugin.id, BlockquoteOptionPlugin);
