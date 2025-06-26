import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class BlockAlignmentOptionPlugin extends Plugin {
    static id = "mass_mailing.BlockAlignmentOption";
    resources = {
        builder_options: [
            {
                template: "html_builder.BlockAlignmentOption",
                selector: ".s_mail_alert .s_alert, .s_mail_blockquote, .s_mail_text_highlight"
            }
        ]
    }
}

registry.category("builder-plugins").add(BlockAlignmentOptionPlugin.id, BlockAlignmentOptionPlugin);
