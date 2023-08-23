/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(PosStore.prototype, "l10n_pt_pos.PosStore", {
    isPortugueseCountry() {
        if (!this.company.country) {
            this.env.services.popup.add(ErrorPopup, {
                title: this.env._t("Missing Country"),
                body: this.env._t("The company %s doesn't have a country set.", this.company.name),
            });
            return false;
        }
        return this.company.country.code === 'PT';
    },
    // Returns the last hash computed
    async l10nPtPosComputeMissingHashes() {
        try {
            return await this.orm.call("pos.order", "l10n_pt_pos_compute_missing_hashes", [this.company.id]);
        } catch {
            this.env.services.popup.add(ErrorPopup, {
                title: this.env._t("Receipt creation failed"),
                body: this.env._t("The receipt QR code couldn't be generated. Please check your internet connection. A temporary ticket will be printed instead."),
            });
        }
    }
});

patch(Order.prototype, "l10n_pt_pos.Order", {
    setup() {
        this._super(...arguments);
        this.l10nPtPosInalterableHash = this.l10nPtPosInalterableHash || false;
        this.l10nPtPosInalterableHashShort = this.l10nPtPosInalterableHashShort || false;
        this.l10nPtPosAtcud = this.l10nPtPosAtcud || false;
        this.l10nPtPosQrCodeStr = this.l10nPtPosQrCodeStr || false;
        this.save_to_db();
    },

    export_for_printing() {
        const result = this._super(...arguments);
        result.l10nPtPosInalterableHash = this.getL10nPtPosInalterableHash();
        result.l10nPtPosInalterableHashShort = this.getL10nPtPosInalterableHashShort();
        result.l10nPtPosAtcud = this.getL10nPtPosAtcud();
        result.l10nPtPosQrCodeStr = this.getL10nPtPosQrCodeStr();
        return result;
    },

    setL10nPtPosInalterableHash(l10nPtPosInalterableHash) {
        this.l10nPtPosInalterableHash = l10nPtPosInalterableHash;
    },

    getL10nPtPosInalterableHash() {
        return this.l10nPtPosInalterableHash;
    },

    setL10nPtPosInalterableHashShort(l10nPtPosInalterableHashShort) {
        this.l10nPtPosInalterableHashShort = l10nPtPosInalterableHashShort;
    },

    getL10nPtPosInalterableHashShort() {
        return this.l10nPtPosInalterableHashShort;
    },

    setL10nPtPosAtcud(l10nPtPosAtcud) {
        this.l10nPtPosAtcud = l10nPtPosAtcud;
    },

    getL10nPtPosAtcud() {
        return this.l10nPtPosAtcud;
    },

    setL10nPtPosQrCodeStr(l10nPtPosQrCodeStr) {
        this.l10nPtPosQrCodeStr = l10nPtPosQrCodeStr;
    },

    getL10nPtPosQrCodeStr() {
        return this.l10nPtPosQrCodeStr;
    },
});
