/** @odoo-module */

import { PosGlobalState, Order } from "@point_of_sale/js/models";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";
import core from "web.core";
import rpc from "web.rpc";

var _t = core._t;

patch(PosGlobalState.prototype, "l10n_pt_pos.PosGlobalState", {
    is_portuguese_country() {
        if (!this.company.country) {
            this.env.services.popup.add(ErrorPopup, {
                title: _t("Missing Country"),
                body: _.str.sprintf(
                    _t("The company %s doesn't have a country set."),
                    this.company.name
                ),
            });
            return false;
        }
        return this.company.country.code === 'PT';
    },
    // Returns the last hash computed
    async l10n_pt_compute_missing_hashes() {
        try {
            return await rpc.query({
                model: 'pos.order',
                method: 'l10n_pt_compute_missing_hashes',
                args: [false, this.env.pos.company.id]
            });
        } catch {
            this.env.services.popup.add(ErrorPopup, {
                title: _t("Receipt creation failed"),
                body: _t("The receipt could not be created. Please check your internet connection."),
            });
        }
    }
});

patch(Order.prototype, "l10n_pt_pos.Order", {
    setup() {
        this._super(...arguments);
        this.blockchain_inalterable_hash = this.blockchain_inalterable_hash || false;
        this.save_to_db();
    },

    export_for_printing() {
        var result = this._super(...arguments);
        result.blockchain_inalterable_hash = this.get_blockchain_inalterable_hash();
        return result;
    },

    set_blockchain_inalterable_hash(blockchain_inalterable_hash) {
        this.blockchain_inalterable_hash = blockchain_inalterable_hash;
    },

    get_blockchain_inalterable_hash() {
        return this.blockchain_inalterable_hash;
    },
});
