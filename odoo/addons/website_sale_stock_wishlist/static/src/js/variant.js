/** @odoo-module **/

import VariantMixin from "@website_sale_stock/js/variant_mixin";
import "@website_sale/js/website_sale";
import { renderToElement } from "@web/core/utils/render";

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
            messageEl.append(
                renderToElement('website_sale_stock_wishlist.product_availability', combination) || ''
            );
        }
    }
};
