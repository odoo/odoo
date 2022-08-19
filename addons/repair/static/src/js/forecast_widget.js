/** @odoo-module */

import { FloatField } from '@web/views/fields/float/float_field';
import { formatDate } from '@web/core/l10n/dates';
import { formatFloat } from '@web/views/fields/formatters';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';

export class RepairForecastWidgetField extends FloatField {
    setup() {
        const { data, fields } = this.props.record;
        this.actionService = useService('action');
        this.orm = useService('orm');
        this.resId = data.id;
        this.product_type = data.product_type
        this.reservedAvailability = formatFloat(
            data.reserved_availability,
            { ...fields.reserved_availability, ...this.nodeOptions }
        );
        this.forecastExpectedDate = formatDate(
            data.forecast_expected_date,
            fields.forecast_expected_date
        );

        if (data.forecast_expected_date && data.schedule_date) {
            this.forecastIsLate = data.forecast_expected_date > data.schedule_date;
        }
        this.willBeFulfilled = data.forecast_availability >= data.product_qty;
        this.moveState = data.move_state;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens the Forecast Report for the `stock.move` product.
     */
    async _openReport(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (!this.resId) {
            return;
        }
        const action = await this.orm.call('repair.line', 'action_product_forecast_report', [this.resId]);
        this.actionService.doAction(action);
    }
}
RepairForecastWidgetField.template = 'repair.ForecastWidget';
RepairForecastWidgetField.displayName = "Repair Forecast Widget";

registry.category('fields').add('repair_forecast_widget', RepairForecastWidgetField);