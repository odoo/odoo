/** @odoo-module **/

import { Orderline } from "@point_of_sale/js/Screens/ProductScreen/Orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline.prototype, "l10n_fr_pos_cert.Orderline", {
    get showOldPrice() {
        const orderline = this.props.line;
        const oldPrice = orderline.get_taxed_lst_unit_price();
        const currentPrice = orderline.get_display_price();
        return (
            !orderline.down_payment_details &&
            !orderline.refunded_orderline_id &&
            orderline.price_changed &&
            this.pos.globalState.is_french_country() &&
            oldPrice !== currentPrice
        );
    },
});
