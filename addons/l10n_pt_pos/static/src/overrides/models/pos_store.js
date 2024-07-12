/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ReprintReasonPopup } from "../../app/reprint_reason_popup/reprint_reason_popup";

patch(PosStore.prototype, {
    async setup(...args) {
        await super.setup(...args);
        const values = await this.data.call("pos.session", "l10n_pt_pos_get_software_info", [
            this.company.id,
            this.config.id,
        ]);
        this.session.l10nPtCertificationNumber = values.l10n_pt_pos_certification_number;
        this.session.l10nPtTrainingMode = values.l10n_pt_training_mode;
    },

    isPortugueseCompany() {
        return this.company.country_id?.code === "PT";
    },

    async l10nPtComputeMissingHashes() {
        // Returns the last hash computed
        try {
            const orderId = Number.isInteger(this.get_order().id) ? this.get_order().id : false;
            return await this.data.call("pos.order", "l10n_pt_pos_compute_missing_hashes", [
                orderId,
                this.config.id,
            ]);
        } catch (e) {
            console.error(e);
            const errorMsg =
                e?.data?.message ||
                _t(
                    "Check your internet connection. If the problem persists, contact Odoo support."
                );
            this.notification.add(_t("The receipt QR code could not be created: %s", errorMsg), {
                type: "warning",
            });
            return {};
        }
    },

    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.isCountryPortugal = this.isPortugueseCompany();
        result.l10nPtTrainingMode = this.session.l10nPtTrainingMode;
        return result;
    },

    async printReceipt(orderVals = this.get_order()) {
        if (!this.isPortugueseCompany() || orderVals["amount_total"] < 0) {
            return super.printReceipt(...arguments);
        }
        await this.l10nPtComputeMissingHashes();
        const order = orderVals.order ? orderVals.order : this.get_order();
        let order_values;

        try {
            order_values = await this.data.call("pos.order", "l10n_pt_get_order_vals", [order.id]);
        } catch (error) {
            this.notification.add(error.data.message, { type: "warning" });
            return {};
        }

        if (order_values.is_reprint) {
            const payload = await makeAwaitable(this.dialog, ReprintReasonPopup, { order });
            if (payload) {
                await this.data.call("pos.order", "post_reprint_reason", [
                    order.id,
                    payload.reprint_reason,
                ]);
            }
        } else {
            await this.data.call("pos.order", "update_l10n_pt_print_version", [order.id]);
        }

        order.name = order_values.name;
        order.isReprint = order_values.is_reprint;
        order.l10nPtPosAtcud = order_values.atcud;
        order.l10nPtPosIdentifier = order_values.document_identifier;
        order.l10nPtPosInalterableHashShort = order_values.hash_short;
        order.l10nPtPosQrCodeStr = order_values.qr_code_str;
        // Return super to allow printing even if the QR code could not be created
        return super.printReceipt(...arguments);
    },
});
