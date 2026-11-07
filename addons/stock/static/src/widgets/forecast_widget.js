import { FloatField, floatField } from "@web/views/fields/float/float_field";
import { formatDate } from "@web/core/l10n/dates";
import { formatFloat } from "@web/views/fields/formatters";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ForecastWidgetField extends FloatField {
    static template = "stock.ForecastWidget";
    async setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");

        const digits = this.props.record.fields.forecast_availability.digits;
        this.options = { digits, thousandsSep: "", decimalPoint: "." };

        const rootContext = this.env.model.root.context;
        if (
            rootContext.onReloadForecastProduct &&
            rootContext.onReloadForecastProduct === this.props.record.data.product_id.id
        ) {
            this._openReport();
        }
    }

    get forecastExpectedDate() {
        return formatDate(
            this.props.record.data.forecast_expected_date,
            this.props.record.fields.forecast_expected_date
        );
    }

    get forecastIsLate() {
        const data = this.props.record.data;
        return (
            data.forecast_expected_date &&
            data.date_deadline &&
            data.forecast_expected_date > data.date_deadline
        );
    }

    get forecastAvailability() {
        return parseFloat(formatFloat(this.props.record.data.forecast_availability, this.options));
    }

    get productQty() {
        return parseFloat(formatFloat(this.props.record.data.product_qty, this.options));
    }

    get willBeFulfilled() {
        return this.forecastAvailability >= this.productQty;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens the Forecast Report for the `stock.move` product.
     */
    async _openReport(ev) {
        ev?.preventDefault();
        ev?.stopPropagation();
        if (!this.props.record.data.is_storable) {
            return;
        }
        if (!this.props.record.resId) {
            await this.env.model.root.save();
            this.env.model.root.context.onReloadForecastProduct =
                this.props.record.data.product_id.id;
            return;
        }
        const action = await this.orm.call("stock.move", "action_product_forecast_report", [
            this.props.record.resId,
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
