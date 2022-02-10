/** @odoo-module **/

import VariantMixin from "website_sale_stock.VariantMixin";
import "website_sale.website_sale";
import ajax from "web.ajax";
import { qweb as QWeb } from "web.core";

const oldLoadStockXML = VariantMixin.loadStockXML;
VariantMixin.loadStockXML = async () => {
    await oldLoadStockXML.apply(this);
    return ajax.loadXML('/website_sale_stock_wishlist/static/src/xml/product_availability.xml', QWeb);
};

const oldChangeCombinationStock = VariantMixin._onChangeCombinationStock;
/**
 * Displays additional info messages regarding the product's
 * stock and the wishlist.
 *
 * @override
 */
VariantMixin._onChangeCombinationStock = function (ev, $parent, combination) {
    return oldChangeCombinationStock.apply(this, arguments).then(() => {
        if (this.el.querySelector('.o_add_wishlist_dyn')) {
            const messageEl = this.el.querySelector('div.availability_messages');
            if (!this.el.querySelector('#stock_wishlist_message')) {
                messageEl.insertAdjacentHTML('beforeend',
                    QWeb.render('website_sale_stock_wishlist.product_availability', combination)
                );
            }
        }
    });
};
