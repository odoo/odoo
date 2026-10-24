/** @odoo-module **/

import { Component, useSubEnv } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        useSubEnv({ model: this.model });
    },
});

export class L10nPlOfflineActions extends Component {
    static template = "l10n_pl_edi_qr_code.OfflineActions";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.action = useService("action");
        this.dialog = useService("dialog");
    }

    get isAvailable() {
        const record = this.env.model.root;
        if (!record.resId) {
            return false;
        }
        const {
            state,
            move_type,
            country_code: countryCode,
            l10n_pl_edi_status: status,
            l10n_pl_edi_ref: reference,
        } = record.data;
        return (
            (countryCode === "PL" &&
                state === "posted" &&
                move_type === "out_invoice" &&
                !status) ||
            (["offline_pending", "offline_failed", "offline_no_submission"].includes(status) &&
                !reference)
        );
    }

    get isCancellation() {
        return ["offline_pending", "offline_failed", "offline_no_submission"].includes(
            this.env.model.root.data.l10n_pl_edi_status
        );
    }

    executeAction() {
        if (!this.isCancellation) {
            return this._execute("action_l10n_pl_edi_prepare_offline");
        }
        this.dialog.add(ConfirmationDialog, {
            body: _t("Cancel the queued Offline24 document and remove its frozen XML and PDF?"),
            confirm: () => this._execute("action_l10n_pl_edi_cancel_offline"),
            confirmClass: "btn-danger",
            confirmLabel: _t("Cancel Offline24"),
        });
    }

    _execute(name) {
        const record = this.env.model.root;
        return this.action.doActionButton({
            type: "object",
            resModel: record.resModel,
            resId: record.resId,
            name,
            context: record.context,
        });
    }
}

export const l10nPlOfflineActionsItem = {
    Component: L10nPlOfflineActions,
    groupNumber: ACTIONS_GROUP_NUMBER,
    isDisplayed: ({ config, model }) =>
        config.viewType === "form" && model?.root?.resModel === "account.move",
};

registry.category("cogMenu").add("l10n-pl-edi-offline-actions", l10nPlOfflineActionsItem);
