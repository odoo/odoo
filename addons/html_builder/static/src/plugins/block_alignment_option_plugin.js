import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BLOCK_ALIGN } from "@html_builder/utils/option_sequence";

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

registry.category("builder-plugins").add(BlockAlignmentOptionPlugin.id, BlockAlignmentOptionPlugin);
