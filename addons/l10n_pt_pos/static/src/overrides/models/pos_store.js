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
    },

    isPortugueseCompany() {
        return this.company.country_id?.code === "PT";
    },

    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.isCountryPortugal = this.isPortugueseCompany();
        return result;
    },

    async l10nPtPrepareOrderForReceipt(order = this.get_order(), { notifyOnError = true } = {}) {
        if (!this.isPortugueseCompany()) {
            return true;
        }
        order.l10nPtCertificationNumber = this.session.l10nPtCertificationNumber;
        if (typeof order?.id !== "number") {
            return false;
        }

        let orderValues;
        try {
            orderValues = await this.data.call("pos.order", "l10n_pt_get_order_vals", [order.id]);
        } catch (error) {
            if (notifyOnError) {
                this.notification.add(
                    error?.data?.message || _t("Unable to load the receipt data."),
                    {
                        type: "warning",
                    }
                );
            }
            return false;
        }

        if (!orderValues || !orderValues.hash_short) {
            return false;
        }

        order.name = orderValues.name;
        order.isReprint = orderValues.is_reprint;
        order.l10nPtPosAtcud = orderValues.atcud;
        order.l10nPtPosIdentifier = orderValues.document_identifier;
        order.l10nPtPosInalterableHashShort = orderValues.hash_short;
        order.l10nPtPosQrCodeStr = orderValues.qr_code_str
            ? order.l10nPtPosGetQrCodeData(orderValues.qr_code_str)
            : false;
        order.l10nPtTrainingMode = orderValues.training_mode;
        return true;
    },

    async printReceipt({ order = this.get_order() } = {}) {
        if (!this.isPortugueseCompany()) {
            return super.printReceipt(...arguments);
        }
        const prepared = await this.l10nPtPrepareOrderForReceipt(order);
        if (!prepared) {
            return {};
        }

        if (order.isReprint) {
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

        // Return super to allow printing even if the QR code could not be created
        return super.printReceipt(...arguments);
    },
});
