odoo.define('stock.forecast_widget', function (require) {
'use strict';

const AbstractField = require('web.AbstractField');
const fieldRegistry = require('web.field_registry');
const field_utils = require('web.field_utils');
const utils = require('web.utils');
const core = require('web.core');
const QWeb = core.qweb;

const ForecastWidgetField = AbstractField.extend({
    supportedFieldTypes: ['float'],

    _render: function () {
        var data = Object.assign({}, this.record.data, {
            forecast_availability_str: field_utils.format.float(
                this.record.data.forecast_availability,
                this.record.fields.forecast_availability,
                this.nodeOptions
            ),
            reserved_availability_str: field_utils.format.float(
                this.record.data.reserved_availability,
                this.record.fields.reserved_availability,
                this.nodeOptions
            ),
            forecast_expected_date_str: field_utils.format.date(
                this.record.data.forecast_expected_date,
                this.record.fields.forecast_expected_date
            ),
        });
        if (data.forecast_expected_date && data.date_deadline) {
            data.forecast_is_late = data.forecast_expected_date > data.date_deadline;
        }
        data.will_be_fulfilled = utils.round_decimals(data.forecast_availability, this.record.fields.forecast_availability.digits[1]) >= utils.round_decimals(data.product_qty, this.record.fields.forecast_availability.digits[1]);

        this.$el.html(QWeb.render('stock.forecastWidget', data));
        this.$('.o_forecast_report_button').on('click', this._onOpenReport.bind(this));
    },

    isSet: function () {
        return true;
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
        if (!this.recordData.id) {
            return;
        }
        this._rpc({
            model: 'stock.move',
            method: 'action_product_forecast_report',
            args: [this.recordData.id],
        }).then(action => {
            action.context = Object.assign(action.context || {}, {
                active_model: 'product.product',
                active_id: this.recordData.product_id.res_id,
            });
            this.do_action(action);
        });
    },
});

const JsonWidget = AbstractField.extend({
    supportedFieldTypes: ['char'],

    _render: function () {
        var value = JSON.parse(this.value);
        if (!value || !value.template) {
            this.$el.html('');
            return;
        }
        $(QWeb.render(value.template, value)).appendTo(this.$el);
    },
});

fieldRegistry.add('forecast_widget', ForecastWidgetField);
fieldRegistry.add('json_widget', JsonWidget);

return ForecastWidgetField;
});
