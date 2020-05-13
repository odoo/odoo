odoo.define('stock.forecast_button_widget', function (require) {
"use strict";

const AbstractField = require('web.AbstractField');
const core = require('web.core');
const registry = require('web.field_registry');

const qweb = core.qweb;

const forecastButtonWidget = AbstractField.extend({
    template: 'forecastButton',
    events: _.extend({}, AbstractField.prototype.events, {
        'click .o_forecast_report_button': '_onOpenReport',
    }),

    init: function (parent, name, record, options) {
        this._super(...arguments);
        const parentState = parent.state.data[0].data.state;
        // The button will be visible only for storable product (so, `product_type` need to be in
        // the same view than this widget) and if the document's state is not draft or cancel.
        this.displayButton = this.record.data.product_type === 'product' && !['draft', 'cancel'].includes(parentState);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _renderReadonly() {
        this.$el.empty();
        if (this.value) {
            this.$el.html(qweb.render(this.template, {
                value: this.value,
                displayButton: this.displayButton,
            }));
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens the Forecast Report for the `stock.move` product.
     *
     * @param {MouseEvent} ev
     */
    _onOpenReport: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const productId = this.recordData.product_id.res_id;
        const resModel = 'product.product';
        this._rpc({
            model: resModel,
            method: 'action_product_forecast_report',
            args: [productId],
        }).then(action => {
            action.context = {
                active_model: resModel,
                active_id: productId,
            };
            this.do_action(action);
        });
    }
});

registry.add('forecast_button', forecastButtonWidget);

});
