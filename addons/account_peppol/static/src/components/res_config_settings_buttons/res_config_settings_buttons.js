/** @odoo-module */

import { escape } from "@web/core/utils/strings";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { Component, markup, useState } from "@odoo/owl";

const waitTime = 60000;

class PeppolSettingsButtons extends Component {
    static props = {
        ...standardWidgetProps,
    };
    static template = "account_peppol.ActionButtons";

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            isSmsButtonDisabled: false,
        });
    }

    get proxyState() {
        return this.props.record.data.account_peppol_proxy_state;
    }

    get migrationPrepared() {
        return this.props.record.data.account_peppol_proxy_state === "active" && Boolean(this.props.record.data.account_peppol_migration_key);
    }

    async _callConfigMethod(methodName, save = false) {
        if (save) {
            await this._save();
        }
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

    async _save () {
        this.env.model.root.save({
            noReload: true,
            stayInEdition: true,
            useSaveErrorDialog: false,
            savePoint: true,
        });
    }

    showConfirmation(warning, methodName) {
        const message = this.env._t(warning);
        const confirmMessage = this.env._t("You will not be able to send or receive Peppol documents in Odoo anymore. Are you sure you want to proceed?");
        this.dialogService.add(ConfirmationDialog, {
            body: markup(
                `<div class="text-danger">${escape(message)}</div>
                <div class="text-danger">${escape(confirmMessage)}</div>`
            ),
            confirm: async () => {
                await this._callConfigMethod(methodName);
            },
            cancel: () => { },
        });
    }

    migrate() {
        this.showConfirmation(
            "This will migrate your Peppol registration away from Odoo. A migration key will be generated. \
            If the other service does not support migration, consider deregistering instead.",
            "button_migrate_peppol_registration"
        )
    }

    deregister() {
        this.showConfirmation(
            "This will delete your Peppol registration.",
            "button_deregister_peppol_participant"
        )
    }

    async updateDetails() {
        // avoid making users click save on the settings
        // and then clicking the update button
        // changes on both the client side and the iap side need to be saved within one method
        await this._callConfigMethod("button_update_peppol_user_data", true);
        this.notification.add(
            this.env._t("Contact details were updated."),
            { type: "success" }
        );
    }

    async checkCode() {
        // avoid making users click save on the settings
        // and then clicking the confirm button to check the code
        await this._callConfigMethod("button_check_peppol_verification_code", true);
    }

    async sendCode() {
        this.state.isSmsButtonDisabled = true;
        // don't allow spamming the button
        setTimeout(() => this.state.isSmsButtonDisabled = false, waitTime);
        await this._callConfigMethod("button_send_peppol_verification_code", true);
    }

    async createUser() {
        await this._callConfigMethod("button_create_peppol_proxy_user", true);
    }
}

registry.category("view_widgets").add("peppol_settings_buttons", {
    component: PeppolSettingsButtons,
});
