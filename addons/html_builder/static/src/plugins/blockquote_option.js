import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

class BlockquoteOptionPlugin extends Plugin {
    static id = "BlockquoteOption";
    resources = {
        builder_options: [
            withSequence(10, {
                template: "html_builder.BlockquoteOption",
                selector: ".s_blockquote",
            }),
        ],
    };
}

registry.category("website-plugins").add(BlockquoteOptionPlugin.id, BlockquoteOptionPlugin);
