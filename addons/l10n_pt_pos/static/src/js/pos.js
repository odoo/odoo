/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(PosStore.prototype, "l10n_pt_pos.PosStore", {
    is_portuguese_country() {
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
    async l10n_pt_pos_compute_missing_hashes() {
        try {
            return await this.orm.call("pos.order", "l10n_pt_pos_compute_missing_hashes", [false, this.company.id]);
        } catch {
            this.env.services.popup.add(ErrorPopup, {
                title: this.env._t("Receipt creation failed"),
                body: this.env._t("The receipt could not be created. Please check your internet connection."),
            });
        }
    }
});

patch(Order.prototype, "l10n_pt_pos.Order", {
    setup() {
        this._super(...arguments);
        this.l10n_pt_pos_inalterable_hash = this.l10n_pt_pos_inalterable_hash || false;
        this.save_to_db();
    },

    export_for_printing() {
        const result = this._super(...arguments);
        result.l10n_pt_pos_inalterable_hash = this.get_l10n_pt_pos_inalterable_hash();
        return result;
    },

    set_l10n_pt_pos_inalterable_hash(l10n_pt_pos_inalterable_hash) {
        this.l10n_pt_pos_inalterable_hash = l10n_pt_pos_inalterable_hash;
    },

    get_l10n_pt_pos_inalterable_hash() {
        return this.l10n_pt_pos_inalterable_hash;
    },
});
