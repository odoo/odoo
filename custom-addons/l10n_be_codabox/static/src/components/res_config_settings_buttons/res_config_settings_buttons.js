/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { Component } from "@odoo/owl";


export class L10nBeCodaboxSettingsButtons extends Component {
    static props = {
        ...standardWidgetProps,
    };
    static template = "l10n_be_codabox.ActionButtons";

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    }

    async saveResConfigSettings(){
        return await this.env.model.root.save({ reload: false });
    }

    async l10nBeCodaboxConnect() {
        await this.saveResConfigSettings();
        await this._callConfigMethod("l10n_be_codabox_connect");
    }

    async l10nBeCodaboxRevoke() {
        await this.saveResConfigSettings();
        this.dialogService.add(ConfirmationDialog, {
            body: _t(
                "This will revoke your access between CodaBox and Odoo."
            ),
            confirm: async () => {
                await this._callConfigMethod("l10n_be_codabox_revoke");
            },
            cancel: () => { },
        });
    }

    async _callConfigMethod(methodName) {
        this.env.onClickViewButton({
            clickParams: {
                name: methodName,
                type: "object",
                noSaveDialog: true,
            },
            getResParams: () =>
                pick(this.env.model.root, "context", "evalContext", "resModel", "resId", "resIds"),
        });
    }
}

registry.category("view_widgets").add("l10n_be_codabox_settings_buttons", {
    component: L10nBeCodaboxSettingsButtons,
});
