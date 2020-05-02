odoo.define('lunch.LunchListRenderer', function (require) {
"use strict";

/**
 * This file defines the Renderer for the Lunch List view, which is an
 * override of the ListRenderer.
 */

var ListRenderer = require('web.ListRenderer');

var LunchListRenderer = ListRenderer.extend({
    events: _.extend({}, ListRenderer.prototype.events, {
        'click .o_data_row': '_onClickListRow',
    }),

    /**
     * @override
     */
    start: function () {
        this.$el.addClass('o_lunch_view o_lunch_list_view');
        return this._super.apply(this, arguments);
    },
    /**
     * Override to add id of product_id in dataset.
     *
     * @override
     */
    _renderRow: function (record) {
        var tr = this._super.apply(this, arguments);
        tr.attr('data-product-id', record.data.id);
        return tr;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Open the add product wizard
     *
     * @private
     * @param {MouseEvent} ev Click event
     */
    _onClickListRow: function (ev) {
        ev.preventDefault();
        var productId = ev.currentTarget.dataset && ev.currentTarget.dataset.productId ? parseInt(ev.currentTarget.dataset.productId) : null;

        if (productId) {
            this.trigger_up('open_wizard', {productId: productId});
        }
    },
});

return LunchListRenderer;

});
