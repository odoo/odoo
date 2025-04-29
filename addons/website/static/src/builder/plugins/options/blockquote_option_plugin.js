import { after, END } from "@html_builder/utils/option_sequence";
import { ANIMATE } from "@website/builder/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";

class BlockquoteOptionPlugin extends Plugin {
    static id = "blockquoteOption";
    selector = ".s_blockquote";
    resources = {
        mark_color_level_selector_params: [{ selector: this.selector }],
        builder_options: [
            withSequence(after(ANIMATE), {
                selector: this.selector,
                OptionComponent: WebsiteBackgroundOption,
                props: {
                    withColors: true,
                    withImages: true,
                    withShapes: true,
                    withColorCombinations: true,
                },
            }),
            withSequence(END, {
                template: "website.BlockquoteOption",
                selector: this.selector,
            }),
        ],
    };
}
// TODO: as in master, the position of a background image does not work
// correctly.
registry.category("website-plugins").add(BlockquoteOptionPlugin.id, BlockquoteOptionPlugin);
