import { after, END } from "@html_builder/utils/option_sequence";
import { ANIMATE } from "@website/builder/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BlockquoteOption } from "./blockquote_option";
import { BLOCKQUOTE_PARENT_HANDLERS } from "@website/builder/plugins/options/utils";
import { withSequence } from "@html_editor/utils/resource";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";

class BlockquoteOptionPlugin extends Plugin {
    static id = "blockquoteOption";
    blockquoteSelector = ".s_blockquote";
    blockquoteExclude = `div:is(${BLOCKQUOTE_PARENT_HANDLERS}) > .s_blockquote`;
    blockquoteDisableWidthApplyTo = ":scope > .s_blockquote";
    websiteBgApplyTo = ":scope > .s_blockquote";
    resources = {
        mark_color_level_selector_params: [{ selector: this.selector }],
        builder_options: [
            {
                OptionComponent: BlockquoteOption,
                selector: this.blockquoteSelector,
                exclude: this.blockquoteExclude,
            },
            {
                OptionComponent: BlockquoteOption,
                selector: BLOCKQUOTE_PARENT_HANDLERS,
                applyTo: this.blockquoteDisableWidthApplyTo,
                props: {
                    disableWidth: true,
                },
            },
            withSequence(after(ANIMATE), {
                OptionComponent: WebsiteBackgroundOption,
                selector: BLOCKQUOTE_PARENT_HANDLERS,
                applyTo: this.websiteBgApplyTo,
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
