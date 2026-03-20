import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import {
    BLOCKQUOTE_DISABLE_WIDTH_APPLY_TO,
    BLOCKQUOTE_PARENT_HANDLERS,
} from "@html_builder/core/utils";
import { BaseWebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { BlockquoteOption, BlockquoteWithoutWidthOption } from "./blockquote_option";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC_BEFORE } from "@html_builder/utils/option_sequence";

export class WebsiteBackgroundBlockquoteOption extends BaseWebsiteBackgroundOption {
    static selector = BLOCKQUOTE_PARENT_HANDLERS;
    static applyTo = BLOCKQUOTE_DISABLE_WIDTH_APPLY_TO;
    static defaultProps = {
        withColors: true,
        withImages: true,
        withShapes: true,
        withColorCombinations: true,
    };
}

class BlockquoteOptionPlugin extends Plugin {
    static id = "blockquoteOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        mark_color_level_selector_params: [
            { selector: BlockquoteOption.selector, exclude: BlockquoteOption.exclude },
            { selector: BLOCKQUOTE_PARENT_HANDLERS, applyTo: BLOCKQUOTE_DISABLE_WIDTH_APPLY_TO },
        ],
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_BEFORE, WebsiteBackgroundBlockquoteOption),
            BlockquoteOption,
            BlockquoteWithoutWidthOption,
        ],
    };
}
// TODO: as in master, the position of a background image does not work
// correctly.
registry.category("website-plugins").add(BlockquoteOptionPlugin.id, BlockquoteOptionPlugin);
