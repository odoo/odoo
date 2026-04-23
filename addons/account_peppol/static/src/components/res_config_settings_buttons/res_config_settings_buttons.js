/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
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
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            isSmsButtonDisabled: false,
        });
    }

    get useParentCompany() {
        return Boolean(this.props.record.data.peppol_use_parent_company);
    }

    get proxyState() {
        return this.props.record.data.account_peppol_proxy_state;
    }

    get migrationPrepared() {
        return this.props.record.data.account_peppol_proxy_state === "active" && Boolean(this.props.record.data.account_peppol_migration_key);
    }

    get ediMode() {
        return this.props.record.data.account_peppol_edi_mode;
    }

    get modeConstraint() {
        return this.props.record.data.account_peppol_mode_constraint;
    }

    get createUserButtonLabel() {
        if (this.proxyState === "sender") {
            return _t("Allow reception");
        }
        const modes = {
            demo: _t("Validate registration (Demo)"),
            test: _t("Validate registration (Test)"),
            prod: _t("Validate registration"),
        }
        return modes[this.ediMode] || _t("Validate registration");
    }

    get deregisterUserButtonLabel() {
        const modes = {
            demo: _t("Switch to Live"),
        }
        return this.modeConstraint !== "demo" && modes[this.ediMode] || _t("Deregister from Peppol");
    }

    async _callConfigMethod(methodName, save = false) {
        if (save) {
            await this._save();
        }
        return this.env.onClickViewButton({
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
        await this.env.model.root.save({ reload: false });
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

    deregister() {
        if (this.ediMode === 'demo') {
            this._callConfigMethod("button_deregister_peppol_participant");
        } else {
            this.showConfirmation(
                "This will delete your Peppol registration.",
                "button_deregister_peppol_participant"
            )
        }
    }

    async deregisterToSender() {
        await this._callConfigMethod("button_peppol_reset_to_sender");
    }

    async allowReception() {
        await this._callConfigMethod("button_peppol_register_sender_as_receiver", true);
        await this.env.model.root.load();
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
        await this._callConfigMethod("button_check_peppol_verification_code", true);
    }

    async sendCode() {
        this.state.isSmsButtonDisabled = true;
        // don't allow spamming the button
        setTimeout(() => this.state.isSmsButtonDisabled = false, waitTime);
        await this._callConfigMethod("button_send_peppol_verification_code", true);
    }

    async createUser() {
        const record = this.props.record;
        try {
            await this._save();
            await this.orm.call(
                record.resModel,
                "button_create_peppol_proxy_user",
                [[record.resId]],
                { context: record.context }
            );
            await this.env.model.root.load();
        } catch (error) {
            const isAlreadyRegisteredError = (
                error.exceptionName?.endsWith("EndpointAlreadyRegisteredError")
                || error.data?.name?.endsWith("EndpointAlreadyRegisteredError")
            );
            if (!isAlreadyRegisteredError) {
                throw error;
            }
            this.dialogService.add(ConfirmationDialog, {
                body: error.data?.message || error.message,
                confirmLabel: _t("OK"),
                cancelLabel: _t("Cancel"),
                confirm: async () => {
                    await this._save();
                    await this.orm.call(
                        record.resModel,
                        "button_create_peppol_proxy_user_sender_only",
                        [[record.resId]],
                        { context: record.context }
                    );
                    await this.env.model.root.load();
                },
                cancel: () => { },
            });
        }
    }
}

registry.category("view_widgets").add("peppol_settings_buttons", {
    component: PeppolSettingsButtons,
});
