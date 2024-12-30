/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { escape } from "@web/core/utils/strings";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { Component, markup, useState } from "@odoo/owl";


class PeppolSettingsButtons extends Component {
    static props = {
        ...standardWidgetProps,
    };
    static template = "account_peppol.ActionButtons";

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        // we have to pass this via context from python
        // because the wizard has to be reopened whenever a button is clicked
        this.state = useState({
            isSmsButtonDisabled: this.props.record.context.disable_sms_verification || false,  // TODO remove in master
            isSettingsView: this.props.record.resModel === 'res.config.settings',
        });
    }

    get proxyState() {
        return this.props.record.data.account_peppol_proxy_state;
    }

    get migrationPrepared() {
        return this.props.record.data.account_peppol_proxy_state === "receiver" && Boolean(this.props.record.data.account_peppol_migration_key);
    }

    get ediMode() {
        return this.props.record.data.edi_mode || this.props.record.data.account_peppol_edi_mode;
    }

    get modeConstraint() {
        return this.props.record.data.mode_constraint;
    }

    get smpRegistration() {
        return this.props.record.data.smp_registration;
    }

    get createButtonLabel() {
        const modes = {
            demo: _t("Activate Peppol (Demo)"),
            test: _t("Activate Peppol (Test)"),
            prod: _t("Activate Peppol"),
        }
        return modes[this.ediMode];
    }

    get deregisterUserButtonLabel() {
        if (['not_registered', 'in_verification'].includes(this.proxyState)) {
            return _t("Discard");
        }
        return _t("Remove from Peppol");
    }

    async _callConfigMethod(methodName) {
        this.env.onClickViewButton({
            clickParams: {
                name: methodName,
                type: "object",
            },
            getResParams: () =>
                pick(this.env.model.root, "context", "evalContext", "resModel", "resId", "resIds"),
        });
    }

    showConfirmation(warning, methodName) {
        const message = _t(warning);
        const confirmMessage = _t("You will not be able to send or receive Peppol documents in Odoo anymore. Are you sure you want to proceed?");
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
        if (this.ediMode === 'demo' || !['sender', 'smp_registration', 'receiver'].includes(this.proxyState)) {
            this._callConfigMethod("button_deregister_peppol_participant");
        } else if (['sender', 'smp_registration', 'receiver'].includes(this.proxyState)) {
            this.showConfirmation(
                "This will delete your Peppol registration.",
                "button_deregister_peppol_participant"
            )
        }
    }

    async updateDetails() {
        // avoid making users click save on the settings
        // and then clicking the update button
        // changes on both the client side and the iap side need to be saved within one method
        await this._callConfigMethod("button_update_peppol_user_data", true);
        this.notification.add(
            _t("Contact details were updated."),
            { type: "success" }
        );
    }

    async checkCode() {
        // avoid making users click save on the settings
        // and then clicking the confirm button to check the code
        await this._callConfigMethod("button_peppol_sender_registration");
    }

    async sendCode() {
        await this._callConfigMethod("button_send_peppol_verification_code");
    }

    async createReceiver() {
        await this._callConfigMethod("button_peppol_smp_registration");
    }
}

registry.category("view_widgets").add("peppol_settings_buttons", {
    component: PeppolSettingsButtons,
});
