/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.SaleUpdateLineButton = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'click a.js_update_line_json': '_onClickOptionQuantityButton',
        'click a.js_add_optional_products': '_onClickAddOptionalProduct',
        'change .js_quantity': '_onChangeOptionQuantity',
    },

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.orderDetail = document.querySelector('table#sales_order_table').dataset;
    },

    /**
     * Calls the route to get updated values of the line and order
     * when the quantity of a product has changed
     *
     * @private
     * @param {integer} order_id
     * @param {Object} params
     * @return {Deferred}
     */
     _callUpdateLineRoute(order_id, params) {
        return rpc("/my/orders/" + order_id + "/update_line_dict", params);
    },

    /**
     * Refresh the UI of the order details
     *
     * @private
     * @param {Object} data: contains order html details
     */
    _refreshOrderUI(data){
        window.location.reload();
    },

    /**
     * Process the change in line quantity
     *
     * @private
     * @param {Event} ev
     */
    async _onChangeOptionQuantity(ev) {
        ev.preventDefault();
        let self = this,
            target = ev.currentTarget,
            quantity = parseInt(target.value);

        const result = await this._callUpdateLineRoute(self.orderDetail.orderId, {
            'line_id': target.dataset.lineId,
            'input_quantity': quantity >= 0 ? quantity : false,
            'access_token': self.orderDetail.token
        });
        this._refreshOrderUI(result);
    },

    /**
     * Reacts to the click on the -/+ buttons
     *
     * @private
     * @param {Event} ev
     */
    async _onClickOptionQuantityButton(ev) {
        ev.preventDefault();
        let self = this,
            target = ev.currentTarget;

        const result = await this._callUpdateLineRoute(self.orderDetail.orderId, {
            'line_id': target.dataset.lineId,
            'remove': target.dataset.remove,
            'unlink': target.dataset.unlink,
            'access_token': self.orderDetail.token
        });
        this._refreshOrderUI(result);
    },

    /**
     * Triggered when optional product added to order from portal.
     *
     * @private
     * @param {Event} ev
     */
     _onClickAddOptionalProduct(ev) {
        ev.preventDefault();
        let self = this,
            target = ev.currentTarget;

        // to avoid double click on link with href.
        target.style.pointerEvents = 'none';

        rpc(
            "/my/orders/" + self.orderDetail.orderId + "/add_option/" + target.dataset.optionId,
            {access_token: self.orderDetail.token}
        ).then((data) => {
            this._refreshOrderUI(data);
        });
    },

});
