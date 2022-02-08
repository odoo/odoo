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
        this.elems = this._getUpdatableElements();
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
            self._updateOrderLineValues($target.closest('tr'), data);
            self._updateOrderValues(data);
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
            var $saleTemplate = $(data['sale_template']);
            if ($saleTemplate.length && data['unlink']) {
                self.$('#portal_sale_content').html($saleTemplate);
                self.elems = self._getUpdatableElements();
            }
            self._updateOrderLineValues($target.closest('tr'), data);
            self._updateOrderValues(data);
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
            if (data) {
                self.$('#portal_sale_content').html($(data['sale_template']));
                self.elems = self._getUpdatableElements();
                self._updateOrderValues(data);
            }
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
    /**
     * Processes data from the server to update the orderline UI
     *
     * @private
     * @param {Element} $orderLine: orderline element to update
     * @param {Object} data: contains order and line updated values
     */
    _updateOrderLineValues($orderLine, data) {
        let linePriceTotal = data.order_line_price_total,
            linePriceSubTotal = data.order_line_price_subtotal,
            $linePriceTotal = $orderLine.find('.oe_order_line_price_total .oe_currency_value'),
            $linePriceSubTotal = $orderLine.find('.oe_order_line_price_subtotal .oe_currency_value');

        if (!$linePriceTotal.length && !$linePriceSubTotal.length) {
            $linePriceTotal = $linePriceSubTotal = $orderLine.find('.oe_currency_value').last();
        }

        $orderLine.find('.js_quantity').val(data.order_line_product_uom_qty);
        if ($linePriceTotal.length && linePriceTotal !== undefined) {
            $linePriceTotal.text(linePriceTotal);
        }
        if ($linePriceSubTotal.length && linePriceSubTotal !== undefined) {
            $linePriceSubTotal.text(linePriceSubTotal);
        }
    },
    /**
     * Processes data from the server to update the UI
     *
     * @private
     * @param {Object} data: contains order and line updated values
     */
    _updateOrderValues(data) {
        let orderAmountTotal = data.order_amount_total,
            orderAmountUntaxed = data.order_amount_untaxed,
            orderAmountUndiscounted = data.order_amount_undiscounted,
            $orderTotalsTable = $(data.order_totals_table);
        if (orderAmountUntaxed !== undefined) {
            this.elems.$orderAmountUntaxed.text(orderAmountUntaxed);
        }

        if (orderAmountTotal !== undefined) {
            this.elems.$orderAmountTotal.text(orderAmountTotal);
        }

        if (orderAmountUndiscounted !== undefined) {
            this.elems.$orderAmountUndiscounted.text(orderAmountUndiscounted);
        }
        if ($orderTotalsTable.length) {
            this.elems.$orderTotalsTable.find('table').replaceWith($orderTotalsTable);
        }
    },
    /**
     * Locate in the DOM the elements to update
     * Mostly for compatibility, when the module has not been upgraded
     * In that case, we need to fall back to some other elements
     *
     * @private
     * @return {Object}: Jquery elements to update
     */
    _getUpdatableElements() {
        let $orderAmountUntaxed = $('[data-id="total_untaxed"]').find('span, b'),
            $orderAmountTotal = $('[data-id="total_amount"]').find('span, b'),
            $orderAmountUndiscounted = $('[data-id="amount_undiscounted"]').find('span, b');

        if (!$orderAmountUntaxed.length) {
            $orderAmountUntaxed = $orderAmountTotal.eq(1);
            $orderAmountTotal = $orderAmountTotal.eq(0).add($orderAmountTotal.eq(2));
        }

        return {
            $orderAmountUntaxed: $orderAmountUntaxed,
            $orderAmountTotal: $orderAmountTotal,
            $orderTotalsTable: $('#total'),
            $orderAmountUndiscounted: $orderAmountUndiscounted,
        };
    }
});
});
