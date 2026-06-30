import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class MassMailingSetupPlugin extends Plugin {
    static id = "mass_mailing_setup_plugin";
    resources = {
        o_editable_selectors: ".o_mail_wrapper_td",
        snippet_preview_dialog_bundles: [
            "mass_mailing.assets_iframe_style",
            "mass_mailing.iframe_add_dialog",
        ],
        clean_for_save_handlers: this.cleanForSave.bind(this),
        powerbox_blacklist_selectors: ".o_mail_wrapper_td",
    };

    setup() {
        const wrapperTd = this.editable.querySelector(".o_mail_wrapper_td");
        wrapperTd?.classList.add("oe_empty");
        wrapperTd?.setAttribute("data-editor-message-default", true);
        wrapperTd?.setAttribute("data-editor-message", _t("DRAG BUILDING BLOCKS HERE"));
    }

    cleanForSave({ root }) {
        const wrapperTd = root.querySelector(".o_mail_wrapper_td.oe_empty");
        wrapperTd?.classList.remove("oe_empty");
        wrapperTd?.removeAttribute("data-editor-message-default");
        wrapperTd?.removeAttribute("data-editor-message");
    }
}

registry.category("mass_mailing-plugins").add(MassMailingSetupPlugin.id, MassMailingSetupPlugin);
