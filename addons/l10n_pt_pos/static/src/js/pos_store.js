/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    isPortugueseCompany() {
        return this.company.country_id?.code === "PT";
    },

    async l10nPtComputeMissingHashes() {
        // Returns the last hash computed
        try {
            const orderId = Number.isInteger(this.get_order().id) ? this.get_order().id : false;
            return await this.data.call("pos.order", "l10n_pt_pos_compute_missing_hashes", [
                orderId,
                this.company.id,
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

    async printReceipt() {
        if (!this.isPortugueseCompany()) {
            return super.printReceipt(...arguments);
        }
        const values = await this.l10nPtComputeMissingHashes();
        this.get_order().name = values.name;
        this.get_order().l10nPtPosAtcud = values.atcud;
        this.get_order().l10nPtPosInalterableHashShort = values.hash_short;
        this.get_order().l10nPtPosQrCodeStr = values.qr_code_str;
        // Return super to allow printing even if the QR code could not be created
        return super.printReceipt(...arguments);
    },
});
