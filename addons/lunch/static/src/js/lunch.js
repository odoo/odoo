odoo.define('lunch.previous_orders', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');
var field_utils = require('web.field_utils');

var QWeb = core.qweb;

var LunchPreviousOrdersWidget = AbstractField.extend({
    events: {
        'click .o_add_button': '_onAddOrder',
    },
    supportedFieldTypes: ['one2many'],
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.lunchData = JSON.parse(this.value);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Used by the widget to render the previous order price like a monetary.
     *
     * @private
     * @param {Object} order
     * @returns {string} the monetary formatting of order price
     */
    _formatValue: function (order) {
        var options = _.extend({}, this.nodeOptions, order);
        return field_utils.format.monetary(order.price, this.field, options);
    },
    /**
     * @private
     * @override
     */
    _render: function () {
        if (this.lunchData !== false) {
            // group data by supplier for display
            var categories = _.groupBy(this.lunchData, 'supplier');
            this.$el.html(QWeb.render('LunchPreviousOrdersWidgetList', {
                formatValue: this._formatValue.bind(this),
                categories: categories,
            }));
        } else {
            return this.$el.html(QWeb.render('LunchPreviousOrdersWidgetNoOrder'));
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAddOrder: function (event) {
        // Get order details from line
        var lineID = parseInt($(event.currentTarget).data('id'));
        if (!lineID) {
            return;
        }
        var values = {
            product_id: {
                id: this.lunchData[lineID].product_id,
                display_name: this.lunchData[lineID].product_name,
            },
            note: this.lunchData[lineID].note,
            price: this.lunchData[lineID].price,
        };

        // create a new order line
        this.trigger_up('field_changed', {
            dataPointID: this.dataPointID,
            changes: {
                order_line_ids: {
                    operation: 'CREATE',
                    data: values,
                },
            },
        });
    },
});

field_registry.add('previous_order', LunchPreviousOrdersWidget);

});
