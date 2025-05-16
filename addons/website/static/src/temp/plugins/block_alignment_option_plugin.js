import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BLOCK_ALIGN } from "@website/website_builder/option_sequence";

class BlockAlignmentOptionPlugin extends Plugin {
    static id = "blockAlignmentOption";
    resources = {
        builder_options: [
            withSequence(BLOCK_ALIGN, {
                template: "html_builder.BlockAlignmentOption",
                selector: ".s_alert, .s_blockquote, .s_text_highlight",
            }),
        ],
    };
}

registry.category("website-plugins").add(BlockAlignmentOptionPlugin.id, BlockAlignmentOptionPlugin);
