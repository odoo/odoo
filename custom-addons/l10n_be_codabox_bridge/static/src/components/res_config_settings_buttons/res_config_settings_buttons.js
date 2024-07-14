/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { onMounted } from "@odoo/owl";
import { L10nBeCodaboxSettingsButtons } from "@l10n_be_codabox/components/res_config_settings_buttons/res_config_settings_buttons";

patch(L10nBeCodaboxSettingsButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
        onMounted(() => {
            const observer = new MutationObserver(this._onConnectionStatusChanged.bind(this));
            const targetNode = document.getElementById('codabox_connection_status');
            observer.observe(targetNode, { childList: true, subtree: true });
            this._handleButtonsDisplay(this.props.record.data.l10n_be_codabox_is_connected);
        });
    },

    async l10nBeCodaboxRevoke() {
        await this.saveResConfigSettings();
        const nb_connections_remaining = await this.orm.call("res.company", "l10n_be_codabox_get_number_connections_remaining", [this.props.record.data.company_id[0]]);
        if (nb_connections_remaining === 0) {
            await this._callConfigMethod("l10n_be_codabox_revoke");  // Will raise an error
            return;
        }
        let message = _t("This will revoke your access between CodaBox and Odoo.");
        if (nb_connections_remaining === 1) {
            message = _t(
                "This will revoke your last access between CodaBox and Odoo.\n" +
                "To be able to connect again to Odoo later on, you will have to " +
                "revoke the connection from myCodaBox platform too."
            );
        }
        this.dialogService.add(ConfirmationDialog, {
            body: message,
            confirm: async () => {
                await this._callConfigMethod("l10n_be_codabox_revoke");
            },
            cancel: () => { },
        });
    },

    _onConnectionStatusChanged(mutationList, observer) {
        const connectionStatusNode = document.getElementById('codabox_connection_status');
        for (const mutation of mutationList) {
            if (
                mutation.target === connectionStatusNode
                && mutation.addedNodes.length > 0
            ){
                this._handleButtonsDisplay(mutation.addedNodes[0].classList.contains('text-success'));
            }
        }
    },

    _handleButtonsDisplay(isConnected) {
        const l10nBeCodaboxConnectButton = document.querySelector("[name='l10nBeCodaboxConnectButton']");
        const l10nBeCodaboxRevokeButton = document.querySelector("[name='l10nBeCodaboxRevokeButton']");
        l10nBeCodaboxConnectButton.classList.remove('d-none');
        l10nBeCodaboxRevokeButton.classList.remove('d-none');
        if (isConnected) {
            l10nBeCodaboxConnectButton.classList.add('d-none');
        } else {
            l10nBeCodaboxRevokeButton.classList.add('d-none');
        }
    },
});
