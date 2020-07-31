odoo.define('stock.forecast_widget', function (require) {
'use strict';

const AbstractField = require('web.AbstractField');
const fieldRegistry = require('web.field_registry');
const core = require('web.core');
const QWeb = core.qweb;

const ForecastWidgetField = AbstractField.extend({
    supportedFieldTypes: ['char'],

    _render: function () {
        const forecastData = JSON.parse(this.value);
        if (!forecastData) {
            this.$el.html('');
        } else {
            this.$el.html(QWeb.render('stock.forecastWidget', forecastData));
            this.$el.on('click', this._onOpenReport.bind(this));
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
    },
});

fieldRegistry.add('forecast_widget', ForecastWidgetField);

return ForecastWidgetField;
});
