odoo.define('sale_management.sale_management', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.SaleUpdateLineButton = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: {
        'click a.js_update_line_json': '_onClick',
        'click a.js_add_optional_products': '_onClickOptionalProduct',
        'change .js_quantity': '_onChangeQuantity'
    },
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.orderDetail = this.$el.find('table#sales_order_table').data();
    },
    /**
     * Process the change in line quantity
     *
     * @private
     * @param {Event} ev
     */
    _onChangeQuantity(ev) {
        ev.preventDefault();
        let self = this,
            $target = $(ev.currentTarget),
            quantity = parseInt($target.val());

        this._callUpdateLineRoute(self.orderDetail.orderId, {
            'line_id': $target.data('lineId'),
            'input_quantity': quantity >= 0 ? quantity : false,
            'access_token': self.orderDetail.token
        }).then((data) => {
            window.location.reload();
        });
    },
    /**
     * Reacts to the click on the -/+ buttons
     *
     * @param {Event} ev
     */
    _onClick(ev) {
        ev.preventDefault();
        let self = this,
            $target = $(ev.currentTarget);
        this._callUpdateLineRoute(self.orderDetail.orderId, {
            'line_id': $target.data('lineId'),
            'remove': $target.data('remove'),
            'unlink': $target.data('unlink'),
            'access_token': self.orderDetail.token
        }).then((data) => {
            window.location.reload();
        });
    },
    /**
     * trigger when optional product added to order from portal.
     *
     * @private
     * @param {Event} ev
     */
    _onClickOptionalProduct(ev) {
        ev.preventDefault();
        let self = this,
            $target = $(ev.currentTarget);
        // to avoid double click on link with href.
        $target.css('pointer-events', 'none');

        this._rpc({
            route: "/my/orders/" + self.orderDetail.orderId + "/add_option/" + $target.data('optionId'),
            params: {access_token: self.orderDetail.token}
        }).then((data) => {
            window.location.reload();
        });
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
        return this._rpc({
            route: "/my/orders/" + order_id + "/update_line_dict",
            params: params,
        });
    },
});
});
