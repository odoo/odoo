import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { escape } from "@web/core/utils/strings";
import { patch } from "@web/core/utils/patch";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { markup } from "@odoo/owl";

const PeppolSettingsButtons = registry.category("view_widgets").get("peppol_settings_buttons").component;

patch(PeppolSettingsButtons.prototype, {
    async createReceiver() {
        if (this.isPdpEdiIdentification && this.proxyState === "sender") {
            this.notification.add(
                _t("To receive invoices through Odoo, deregister this Sender Only connection, then activate electronic invoicing again and choose Migrate to Odoo."),
                { title: _t("Migrate reception to Odoo"), type: "info", sticky: true }
            );
            return;
        }
        return super.createReceiver();
    },

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
});
