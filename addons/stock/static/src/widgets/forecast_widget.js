import { FloatField, floatField } from "@web/views/fields/float/float_field";
import { formatDate } from "@web/core/l10n/dates";
import { formatFloat } from "@web/views/fields/formatters";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ForecastWidgetField extends FloatField {
    static template = "stock.ForecastWidget";
    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
    }

    get resId() {
        return this.props.record.resId;
    }

    get forecastExpectedDate() {
        const { data, fields } = this.props.record;
        return formatDate(
            data.forecast_expected_date,
            fields.forecast_expected_date
        );
    }

    get forecastIsLate() {
        const { data } = this.props.record;
        return Boolean(data.forecast_expected_date && data.date_deadline &&
            data.forecast_expected_date > data.date_deadline);
    }

    get quantityFormatOptions() {
        const digits = this.props.record.fields.forecast_availability.digits;
        return { digits, thousandsSep: "", decimalPoint: "." };
    }

    get product_qty() {
        return parseFloat(formatFloat(this.props.record.data.product_qty, this.quantityFormatOptions));
    }

    get willBeFulfilled() {
        const { data } = this.props.record;
        const options = this.quantityFormatOptions;
        const forecast_availability = parseFloat(formatFloat(data.forecast_availability, options));
        return forecast_availability >= this.product_qty;
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
        if (!this.resId || !this.props.record.data.is_storable) {
            return;
        }
        const action = await this.orm.call("stock.move", "action_product_forecast_report", [
            this.resId,
        ]);
        this.actionService.doAction(action);
    }

    get decoration() {
        if (!this.forecastExpectedDate && this.willBeFulfilled){
            return "text-bg-success"
        } else if (this.forecastExpectedDate && this.willBeFulfilled){
            return this.forecastIsLate ? 'text-bg-danger' : 'text-bg-warning'
        } else {
            return 'text-bg-danger'
        }

    }
}

export const forecastWidgetField = {
    ...floatField,
    component: ForecastWidgetField,
};

registry.category("fields").add("forecast_widget", forecastWidgetField);
