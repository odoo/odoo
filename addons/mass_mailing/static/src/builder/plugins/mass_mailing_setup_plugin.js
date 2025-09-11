import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class MassMailingSetupPlugin extends Plugin {
    static id = "mass_mailing_setup_plugin";
    resources = {
        o_editable_selectors: ".o_mail_wrapper_td",
        snippet_preview_dialog_bundles: [
            "mass_mailing.assets_iframe_style",
            "mass_mailing.iframe_add_dialog",
        ],
    };
}

registry.category("mass_mailing-plugins").add(MassMailingSetupPlugin.id, MassMailingSetupPlugin);
