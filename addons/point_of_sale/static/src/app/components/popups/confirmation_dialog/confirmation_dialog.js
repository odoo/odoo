import {
    alertDialogProps,
    ConfirmationDialog,
    confirmationDialogProps,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { t } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { SyncPopup } from "@point_of_sale/app/components/popups/sync_popup/sync_popup";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";

patch(ConfirmationDialog.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },
    async _cancel() {
        this.props.getPayload && this.props.getPayload(false);
        return this.execButton(this.props.cancel);
    },
    async _confirm() {
        this.props.getPayload && this.props.getPayload(true);
        return this.execButton(this.props.confirm);
    },
    async _dismiss() {
        this.props.getPayload && this.props.getPayload(false);
        return this.execButton(this.props.dismiss || this.props.cancel);
    },
    async _reloadData() {
        this.props.close();
        if (this.pos.config?.module_pos_restaurant) {
            try {
                await this.pos.syncAllOrders();
            } catch (error) {
                logPosMessage("Failed to sync orders:", error);
            }
        }
        this.pos.dialog.add(SyncPopup, {
            title: _t("Reload Data"),
            confirm: (fullReload) => this.pos.reloadData(fullReload),
        });
    },
});

Object.assign(confirmationDialogProps, {
    getPayload: t.function().optional(),
    showReloadButton: t.boolean().optional(false),
});

Object.assign(alertDialogProps, {
    getPayload: t.function().optional(),
    showReloadButton: t.boolean().optional(false),
});
