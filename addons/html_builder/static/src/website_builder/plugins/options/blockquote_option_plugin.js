import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { WebsiteBackgroundOption } from "@html_builder/website_builder/plugins/options/background_option";

class BlockquoteOptionPlugin extends Plugin {
    static id = "blockquoteOption";
    resources = {
        builder_options: [
            withSequence(30, {
                selector: ".s_blockquote",
                OptionComponent: WebsiteBackgroundOption,
                props: {
                    withColors: true,
                    withImages: true,
                    withShapes: true,
                    withGradient: true,
                    withColorCombinations: true,
                },
            }),
            withSequence(40, {
                template: "website.BlockquoteOption",
                selector: ".s_blockquote",
            }),
        ],
    };
}
// TODO: as in master, the position of a background image does not work
// correctly.
registry.category("website-plugins").add(BlockquoteOptionPlugin.id, BlockquoteOptionPlugin);
