import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class WidthOptionPlugin extends Plugin {
    static id = "mass_mailing.WidthOption";
    resources = {
        patch_builder_options: [
            {
                target_name: "widthOption",
                target_element: "selector",
                method: "add",
                value: ".s_mail_alert .s_alert, .s_mail_blockquote, .s_mail_text_highlight",
            },
        ],
    };
}

registry.category("mass_mailing-plugins").add(WidthOptionPlugin.id, WidthOptionPlugin);
