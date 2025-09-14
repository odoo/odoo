import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class VerticalAlignmentOptionPlugin extends Plugin {
    static id = "mass_mailing.VerticalAlignmentOption";
    resources = {
        patch_builder_options: [
            {
                target_name: "verticalAlignmentOption",
                target_element: "selector",
                method: "add",
                value: ".s_mail_block_event",
            },
        ],
    };
}

registry
    .category("mass_mailing-plugins")
    .add(VerticalAlignmentOptionPlugin.id, VerticalAlignmentOptionPlugin);
