import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { escape } from "@web/core/utils/strings";
import { patch } from "@web/core/utils/patch";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { markup } from "@odoo/owl";

const PeppolSettingsButtons = registry.category("view_widgets").get("peppol_settings_buttons").component;

patch(PeppolSettingsButtons.prototype, {
    get deregisterUserButtonLabel() {
        if (this.isPdpEdiIdentification && this.proxyState === "sender") {
            return _t("Deregister");
        }
        return super.deregisterUserButtonLabel;
    },

    showConfirmation(warning, methodName) {
        if (!this.isPdpEdiIdentification || this.proxyState !== "sender") {
            return super.showConfirmation(warning, methodName);
        }
        this.dialogService.add(ConfirmationDialog, {
            body: markup(
                `<div class="text-danger">${escape(_t("This will disconnect your Sender Only connection from Odoo."))}</div>
                <div>${escape(_t("You will no longer be able to send invoices through Odoo. Your existing receiving platform registration will not be changed."))}</div>`
            ),
            confirm: async () => {
                await this._callConfigMethod(methodName);
            },
            cancel: () => {},
        });
    },

    async createReceiver() {
        if (this.isPdpEdiIdentification && this.proxyState === "sender") {
            this.dialogService.add(ConfirmationDialog, {
                body: markup(
                    `<div>${escape(_t("You must deregister your current Sender Only connection before registering as a receiver."))}</div>
                    <div>${escape(_t("After deregistration, register again to migrate your reception to Odoo."))}</div>`
                ),
                confirm: () => {},
                cancel: () => {},
            });
            return;
        }
        await super.createReceiver();
    },
});
