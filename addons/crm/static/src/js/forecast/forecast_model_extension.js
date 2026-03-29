/** @odoo-module */
import ActionModel from 'web.ActionModel';

/**
 * This file contains the logic behind a special "Forecast" filter.
 * Any such filter should set the context key {forecast_filter: 1}
 * Another context key must also be set for the view using this model extension:
 * {forecast_field: "date_field_name"}, which represents the date/time field on which
 * the forecast should be applied
 *
 * The main purpose is to be able to modify the domain depending on the groupby granularity
 * when the field is a `date/time` field and is the `forecast_field`. The domain should filter
 * records from the period (granularity) containing "now", or those where the forecast_field
 * is not set.
 * example:
 *  today:          2021-04-21
 *  granularity:    month
 *  field name:     date_field
 *  -> the domain would be: ['&', ['date_field', '=', false], ['date_field', '>=', '2021-04-01']]
 */
const DATE_FORMAT = {
    datetime: "YYYY-MM-DD HH:mm:ss",
    date: "YYYY-MM-DD",
};
class ForecastModelExtension extends ActionModel.Extension {
    /**
     * @override
     */
    dispatch() {
        this.state.forecastStart = null;
    }

    /**
     * @override
     */
    get(property) {
        switch (property) {
            case "domain": return this.getDomain();
            default: return super.get(...arguments);
        }
    }

    /**
     * Adds a domain constraint to only get records from the start of the period containing "now",
     * only if a "Forecast" filter is active
     *
     * @returns {Array[]}
     */
    getDomain() {
        const forecastField = this.config.context.forecast_field;
        if (!forecastField) {
            return null;
        }
        const filters = this.config.get("filters").flat();
        const forecastFilter = filters.some((f) => {
            return f.isActive && f.context && f.context.forecast_filter;
        });
        if (!forecastFilter) {
            return null;
        }
        const forecastStart = this._getForecastStart(forecastField);
        return ["|", [forecastField, "=", false], [forecastField, ">=", forecastStart]];
    }

    /**
     * @override
     */
    prepareState() {
        super.prepareState(...arguments);
        Object.assign(this.state, {
            forecastStart: null,
        });
    }

    /**
     * Returns a date (datetime) starting from a forecast field of type date (resp. datetime).
     * The value returned depends on the active groubys.
     * @private
     * @param {string} forecastField name of the date/time field related to the forecast
     * @returns {string}
     */
    _getForecastStart(forecastField) {
        if (!this.state.forecastStart) {
            const type = this.config.fields[forecastField].type;
            const groupBy = this.config.get("groupBy").flat();
            const firstForecastGroupBy = groupBy.find((gb) => gb.includes(forecastField));
            let granularity = "month";
            if (firstForecastGroupBy) {
                granularity = firstForecastGroupBy.split(":")[1] || "month";
            } else if (groupBy.length) {
                // there is a groupBy, but it is not the forecast_field
                granularity = "day";
            }
            let startMoment = moment().startOf(granularity);
            // The server needs a date/time in UTC, but to avoid a day shift in case
            // of date, we only need to consider it for datetime fields
            if (type === "datetime") {
                startMoment = moment.utc(startMoment);
            }
            const format = DATE_FORMAT[type];
            this.state.forecastStart = startMoment.locale("en").format(format);
        }
        return this.state.forecastStart;
    }
}

ActionModel.registry.add("forecast", ForecastModelExtension, 20);

export default ForecastModelExtension;
