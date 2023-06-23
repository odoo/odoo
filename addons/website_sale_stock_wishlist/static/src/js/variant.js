/** @odoo-module **/

import VariantMixin from "@website_sale_stock/js/variant_mixin";
import "@website_sale/js/website_sale";
import { qweb as QWeb } from "@web/legacy/js/services/core";

const oldChangeCombinationStock = VariantMixin._onChangeCombinationStock;
/**
 * Displays additional info messages regarding the product's
 * stock and the wishlist.
 *
 * @override
 */
VariantMixin._onChangeCombinationStock = function (ev, $parent, combination) {
    oldChangeCombinationStock.apply(this, arguments);
    if (this.el.querySelector('.o_add_wishlist_dyn')) {
        const messageEl = this.el.querySelector('div.availability_messages');
        if (messageEl && !this.el.querySelector('#stock_wishlist_message')) {
            messageEl.insertAdjacentHTML('beforeend',
                QWeb.render('website_sale_stock_wishlist.product_availability', combination)
            );
        }
    }
};
