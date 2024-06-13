/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(PosStore.prototype, {
    is_french_country() {
        const french_countries = ["FR", "MF", "MQ", "NC", "PF", "RE", "GF", "GP", "TF"];
        if (!this.company.country_id) {
            this.dialog.add(AlertDialog, {
                title: _t("Missing Country"),
                body: _t("The company %s doesn't have a country set.", this.company.name),
            });
            return false;
        }
        return french_countries.includes(this.company.country_id?.code);
    },
    disallowLineQuantityChange() {
        const result = super.disallowLineQuantityChange(...arguments);
        const selectedOrderLine = this.get_order().get_selected_orderline();
        //Note: is_reward_line is a field in the pos_loyalty module, it can be undefined if not installed
        if (selectedOrderLine?.is_reward_line) {
            //Always allow quantity change for reward lines
            return false || result;
        }
        return this.is_french_country() || result;
    },
});
