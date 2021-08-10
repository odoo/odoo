/** @odoo-module **/

import publicWidget from "web.public.widget";
import "website_sale.website_sale";
import ajax from "web.ajax";
import { qweb as QWeb } from "web.core";

const loadXml = async () => {
    return ajax.loadXML('/website_sale_stock_wishlist/static/src/xml/product_availability.xml', QWeb);
};

publicWidget.registry.WebsiteSale.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Displays additional info messages regarding the product's
     * stock and the wishlist.
     *
     * @override
     */
    _onChangeCombination: async function (ev, $parent, combination) {
        this._super(...arguments);
        loadXml().then(() => {
            if (this.el.querySelector('.o_add_wishlist_dyn')) {
                const messageEl = this.el.querySelector('div.availability_messages');
                messageEl.insertAdjacentHTML('beforeend', QWeb.render('website_sale_stock_wishlist.product_availability', combination));
            }
        });
    },
});
