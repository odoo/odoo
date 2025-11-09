import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { after, WIDTH } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class AlertOption extends BaseOptionComponent {
    static template = "mass_mailing.AlertOption";
    static selector = ".s_mail_alert .s_alert";
}

export class BorderOption extends BaseOptionComponent {
    static template = "mass_mailing.BorderOption";
    static selector = ".s_mail_alert .s_alert";
    static components = { BorderConfigurator };
}

class AlertOptionPlugin extends Plugin {
    static id = "mass_mailing.AlertOption";
    resources = {
        builder_options: [
            withSequence(after(WIDTH), AlertOption),
            withSequence(after(WIDTH), BorderOption),
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
