/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order } from "@point_of_sale/app/store/models";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PosStore.prototype, {
    is_french_country() {
        var french_countries = ["FR", "MF", "MQ", "NC", "PF", "RE", "GF", "GP", "TF"];
        if (!this.company.country_id) {
            this.env.services.dialog.add(AlertDialog, {
                title: _t("Missing Country"),
                body: _t("The company %s doesn't have a country set.", this.company.name),
            });
            return false;
        }
        return french_countries.includes(this.company.country_id?.code);
    },
});

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this.l10n_fr_hash = this.l10n_fr_hash || false;
        this.save_to_db();
    },
    export_for_printing() {
        var result = super.export_for_printing(...arguments);
        result.l10n_fr_hash = this.get_l10n_fr_hash();
        if (this.pos.is_french_country()){
            result.pos_qr_code = false;
        }
        return result;
    },
    set_l10n_fr_hash(l10n_fr_hash) {
        this.l10n_fr_hash = l10n_fr_hash;
    },
    get_l10n_fr_hash() {
        return this.l10n_fr_hash;
    },
    wait_for_push_order() {
        var result = super.wait_for_push_order(...arguments);
        result = Boolean(result || this.pos.is_french_country());
        return result;
    },
});
