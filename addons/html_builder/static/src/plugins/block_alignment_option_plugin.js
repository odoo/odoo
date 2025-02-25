import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

class BlockAlignmentOptionPlugin extends Plugin {
    static id = "blockAlignmentOption";
    resources = {
        builder_options: [
            withSequence(30, {
                template: "html_builder.BlockAlignmentOption",
                selector: ".s_alert, .s_blockquote, .s_text_highlight",
            }),
        ],
    };
}

registry.category("website-plugins").add(BlockAlignmentOptionPlugin.id, BlockAlignmentOptionPlugin);
