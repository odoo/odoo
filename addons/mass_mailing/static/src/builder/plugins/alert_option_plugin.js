import { after, WIDTH } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class AlertOptionPlugin extends Plugin {
    static id = "mass_mailing.AlertOption";
    resources = {
        builder_options: [
            withSequence(after(WIDTH), {
                selector: ".s_mail_alert .s_alert",
                template: "mass_mailing.AlertOption",
            }),
            withSequence(after(WIDTH), {
                selector: ".s_mail_alert .s_alert",
                template: "mass_mailing.BorderOption",
            }),
        ],
        patch_builder_options: [
            {
                target_name: "alertTypeOption",
                target_element: "exclude",
                method: "replace",
                value: ".s_mail_alert .s_alert",
            },
        ],
    };
}

registry.category("mass_mailing-plugins").add(AlertOptionPlugin.id, AlertOptionPlugin);
