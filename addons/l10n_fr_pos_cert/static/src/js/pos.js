/** @odoo-module */

import { PosGlobalState, Order, Orderline } from "@point_of_sale/js/models";
import core from "web.core";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/js/Popups/ErrorPopup";

var _t = core._t;

patch(PosGlobalState.prototype, "l10n_fr_pos_cert.PosGlobalState", {
    is_french_country() {
        var french_countries = ["FR", "MF", "MQ", "NC", "PF", "RE", "GF", "GP", "TF"];
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
        return _.contains(french_countries, this.company.country.code);
    },
    disallowLineQuantityChange() {
        let result = this._super(...arguments);
        let selectedOrderLine = this.selectedOrder.get_selected_orderline();
        //Note: is_reward_line is a field in the pos_loyalty module
        if (selectedOrderLine && selectedOrderLine.is_reward_line) {
            //Always allow quantity change for reward lines
            return false || result;
        }
        return this.is_french_country() || result;
    },
});

patch(Order.prototype, "l10n_fr_pos_cert.Order", {
    setup() {
        this._super(...arguments);
        this.l10n_fr_hash = this.l10n_fr_hash || false;
        this.save_to_db();
    },
    export_for_printing() {
        var result = this._super(...arguments);
        result.l10n_fr_hash = this.get_l10n_fr_hash();
        return result;
    },
    set_l10n_fr_hash(l10n_fr_hash) {
        this.l10n_fr_hash = l10n_fr_hash;
    },
    get_l10n_fr_hash() {
        return this.l10n_fr_hash;
    },
    wait_for_push_order() {
        var result = this._super(...arguments);
        result = Boolean(result || this.pos.is_french_country());
        return result;
    },
    destroy(option) {
        // SUGGESTION: It's probably more appropriate to apply this restriction
        // in the TicketScreen.
        if (
            option &&
            option.reason == "abandon" &&
            this.pos.is_french_country() &&
            this.get_orderlines().length
        ) {
            this.env.services.popup.add(ErrorPopup, {
                title: _t("Fiscal Data Module error"),
                body: _t("Deleting of orders is not allowed."),
            });
        } else {
            this._super(...arguments);
        }
    },
});

patch(Orderline.prototype, "l10n_fr_pos_cert.Orderline", {
    can_be_merged_with(orderline) {
        if (!this.pos.is_french_country()) {
            return this._super(...arguments);
        }
        const order = this.pos.get_order();
        const orderlines = order.orderlines;
        const lastOrderline = order.orderlines.at(orderlines.length - 1);

        if (lastOrderline.product.id !== orderline.product.id || lastOrderline.quantity < 0) {
            return false;
        } else {
            return this._super(...arguments);
        }
    },
});
