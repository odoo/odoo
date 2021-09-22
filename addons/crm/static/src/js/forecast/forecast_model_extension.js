/** @odoo-module */
import ActionModel from 'web.ActionModel';
import { Domain } from "@web/core/domain";

/**
 * This file contains the logic behind a special "Forecast" filter.
 * Any such filter should set the context key {forecast_field: "date_field_name"}
 * which represents the date/time field on which the forecast should be applied
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
     * @returns {any}
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
        const filters = this.config.get('filters').flat();
        const forecastFilters = filters.filter(f => f.isActive && f.context && f.context.forecast_field);
        if (!forecastFilters.length) {
            return null;
        }
        const addNextFilterDomain = (domain, filter) => {
            const forecastField = filter.context.forecast_field;
            const forecastStart = this._getForecastStart(forecastField);
            const filterDomain = ['|', [forecastField, '=', false],
                [forecastField, '>=', forecastStart]
            ];
            return (!domain) ? filterDomain : Domain.and([domain, filterDomain]).ast.value;
        };
        return forecastFilters.reduce(addNextFilterDomain, null);
    }

    /**
     * The forecastStart date/time is mostly dependent on a context key in the filter:
     * forecast_field -> a custom filter with this context key in its own context should be present
     * and active in order to get the modified domain
     *
     * And is also dependent on whether forecast_field is one of the groupby fields:
     * If the forecast_field is present in the groupby, the related granularity is used
     * If no granularity is specified, or if there is no groupby, the default is "month"
     * If there is a groupby, but not the forecast_field, "day" is used (the filter will get data
     * from 00:00:00 today, browser time)
     *
     * @private
     * @param {string} forecastField name of the date/time field related to the forecast
     * @returns {string}
     */
    _getForecastStart(forecastField) {
        const type = this.config.fields[forecastField].type;
        const groupBy = this.config.get('groupBy').flat();
        const firstForecastGroupBy = groupBy.find(gb => gb.includes(forecastField));
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
        if (this.config.fields[forecastField].type === "datetime") {
            startMoment = moment.utc(startMoment);
        }
        const format = DATE_FORMAT[type];
        return startMoment.format(format);
    }
}

ActionModel.registry.add("forecast", ForecastModelExtension, 20);

export default ForecastModelExtension;
