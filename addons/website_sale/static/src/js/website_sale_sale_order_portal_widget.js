/** @odoo-module **/

import publicWidget from 'web.public.widget';
import wUtils from 'website.utils';


publicWidget.registry.SaleOrderPortal = publicWidget.Widget.extend({
    selector: '.order_again_btn',
    events: {
        'click': '_onClickOrderAgain',
    },

    async _onClickOrderAgain(ev) {
        console.log("onClickOrderAgain");
        const saleOrderId = ev.currentTarget.dataset.saleOrderId;
        let response = await this._rpc({
            model: 'sale.order.line',
            method: 'search_read',
            domain: [
                ["order_id", "=", parseInt(saleOrderId)],
            ],
        });
        const saleOrderLines = response.filter(saleOrderLine => saleOrderLine.product_id);

        debugger
        saleOrderLines.forEach(line => {
            const params = {
                product_id: line.product_id[0],
                set_qty: line.product_uom_qty
            };
            this._rpc({
                route: "/shop/cart/update_json",
                params: params,
            })
        });

    }
});

export default publicWidget.registry.SaleOrderPortal;
