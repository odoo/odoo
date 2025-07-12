import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class MassMailingSetupPlugin extends Plugin {
    static id = "mass_mailing_setup_plugin";
    resources = {
        o_editable_selectors: ".o_mail_wrapper_td",
    };
}

registry.category("mass_mailing-plugins").add(MassMailingSetupPlugin.id, MassMailingSetupPlugin);
