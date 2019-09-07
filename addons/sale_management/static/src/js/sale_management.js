odoo.define('sale_management.sale_management', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.SaleUpdateLineButton = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar a.js_update_line_json',
    events: {
        'click': '_onClick',
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.elems = self._getUpdatableElements();
                 self.elems.$lineQuantity.change(function (ev) {
                    var quantity = parseInt(this.value);
                    self._onChangeQuantity(quantity);
                });
            });
        },
    /**
     * Process the change in line quantity
     *
     * @private
     * @param {Int} quantity, the new quantity of the line
     *    If not present it will increment/decrement the existing quantity
     */
    _onChangeQuantity: function (quantity) {
        var href = this.$el.attr("href");
        var orderID = href.match(/my\/orders\/([0-9]+)/);
        var lineID = href.match(/update_line\/([0-9]+)/);
        var params = {
                'line_id': parseInt(lineID[1]),
                'remove': this.$el.is('[href*="remove"]'),
                'unlink': this.$el.is('[href*="unlink"]'),
                'input_quantity': quantity >= 0 ? quantity : false,
        };
            var token = href.match(/token=([\w\d-]*)/)[1];
        if (token) {
            params['access_token'] = token;
        }

        orderID = parseInt(orderID[1]);
        this._callUpdateLineRoute(orderID, params).then(this._updateOrderValues.bind(this));
    },
    /**
     * Reacts to the click on the -/+ buttons
     *
     * @param {Event} ev
     */
    _onClick: function (ev) {
        ev.preventDefault();
        return this._onChangeQuantity();
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
    _callUpdateLineRoute: function (order_id, params) {
        var url = "/my/orders/" + order_id + "/update_line_dict";
        return this._rpc({
            route: url,
            params: params,
        });
    },
    /**
     * Processes data from the server to update the UI
     *
     * @private
     * @param {Object} data: contains order and line updated values
     */
    _updateOrderValues: function (data) {
        if (!data) {
            window.location.reload();
        }

        var orderAmountTotal = data.order_amount_total;
        var orderAmountUntaxed = data.order_amount_untaxed;
        var orderAmountTax = data.order_amount_tax;
        var orderAmountUndiscounted = data.order_amount_undiscounted;
        var orderTotalsTable = $(data.order_totals_table);

        var lineProductUomQty = data.order_line_product_uom_qty;
        var linePriceTotal = data.order_line_price_total;
        var linePriceSubTotal = data.order_line_price_subtotal;

        this.elems.$lineQuantity.val(lineProductUomQty);

        if (this.elems.$linePriceTotal.length && linePriceTotal !== undefined) {
            this.elems.$linePriceTotal.text(linePriceTotal);
        }
        if (this.elems.$linePriceSubTotal.length && linePriceSubTotal !== undefined) {
            this.elems.$linePriceSubTotal.text(linePriceSubTotal);
        }

        if (orderAmountUntaxed !== undefined) {
            this.elems.$orderAmountUntaxed.text(orderAmountUntaxed);
        }

        if (orderAmountTotal !== undefined) {
            this.elems.$orderAmountTotal.text(orderAmountTotal);
        }

        if (orderAmountUndiscounted !== undefined) {
            this.elems.$orderAmountUndiscounted.text(orderAmountUndiscounted);
        }
        if (orderTotalsTable) {
            this.elems.$orderTotalsTable.find('table').replaceWith(orderTotalsTable);
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
    _getUpdatableElements: function () {
        var $parentTr = this.$el.parents('tr:first');
        var $linePriceTotal = $parentTr.find('.oe_order_line_price_total .oe_currency_value');
        var $linePriceSubTotal = $parentTr.find('.oe_order_line_price_subtotal .oe_currency_value');

        if (!$linePriceTotal.length && !$linePriceSubTotal.length) {
            $linePriceTotal = $linePriceSubTotal = $parentTr.find('.oe_currency_value').last();
        }

        var $orderAmountUntaxed = $('[data-id="total_untaxed"]').find('span, b');
        var $orderAmountTotal = $('[data-id="total_amount"]').find('span, b');
        var $orderAmountUndiscounted = $('[data-id="amount_undiscounted"]').find('span, b');

        if (!$orderAmountUntaxed.length) {
            $orderAmountUntaxed = $orderAmountTotal.eq(1);
            $orderAmountTotal = $orderAmountTotal.eq(0).add($orderAmountTotal.eq(2));
        }

        return {
            $lineQuantity: this.$el.closest('.input-group').find('.js_quantity'),
            $linePriceSubTotal: $linePriceSubTotal,
            $linePriceTotal: $linePriceTotal,
            $orderAmountUntaxed: $orderAmountUntaxed,
            $orderAmountTotal: $orderAmountTotal,
            $orderTotalsTable: $('#total'),
            $orderAmountUndiscounted: $orderAmountUndiscounted,
        };
    }
});
});
