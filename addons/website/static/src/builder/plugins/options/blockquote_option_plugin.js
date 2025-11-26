import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BLOCKQUOTE_PARENT_HANDLERS } from "@html_builder/core/utils";

export const SPECIAL_BLOCKQUOTE_SELECTOR = `${BLOCKQUOTE_PARENT_HANDLERS} > .s_blockquote`;
export const BLOCKQUOTE_DISABLE_WIDTH_APPLY_TO = ":scope > .s_blockquote";

export class BlockquoteOptionPlugin extends Plugin {
    static id = "blockquoteOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        mark_color_level_selector_params: [
            { selector: ".s_blockquote", exclude: SPECIAL_BLOCKQUOTE_SELECTOR },
            { selector: BLOCKQUOTE_PARENT_HANDLERS, applyTo: BLOCKQUOTE_DISABLE_WIDTH_APPLY_TO },
        ],
        builder_options_context: {
            specialBlockquoteSelector: SPECIAL_BLOCKQUOTE_SELECTOR,
            blockquoteDisableWidthApplyTo: BLOCKQUOTE_DISABLE_WIDTH_APPLY_TO,
            blockquoteParentHandlers: BLOCKQUOTE_PARENT_HANDLERS,
        },
    };
}
// TODO: as in master, the position of a background image does not work
// correctly.
registry.category("website-plugins").add(BlockquoteOptionPlugin.id, BlockquoteOptionPlugin);
