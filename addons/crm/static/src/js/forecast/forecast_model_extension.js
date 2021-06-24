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
     * @returns {any}
     */
    get(property) {
        switch (property) {
            case "domain": return this.getDomain();
            default: return super.get(...arguments);
        }
    }

    /**
     * @override
     */
    prepareState() {
        super.prepareState(...arguments);
        Object.assign(this.state, {
            forecastField: null,  // {string} forecast_field from the context (name)
            forecastFieldType: null,  // {string} forecast_field type (date or datetime)
            forecastFilter: null,  // {boolean} if the "Forecast" filter is active
            forecastStart: null,  // {string} limiting bound of the filter (if active)
                                  // -> starting date before which records are filtered out
        });
    }

    /**
     * The state needs to be recomputed each time the parent model initiates a load action.
     *
     * @override
     * @returns {Promise}
     */
    callLoad() {
        this._computeState();
        return super.callLoad(...arguments);
    }

    /**
     * Adds a domain constraint to only get records from the start of the period containing "now",
     * only if the "Forecast" filter is active
     *
     * @returns {Array[]}
     */
    getDomain() {
        return !this.state.forecastFilter ? null :
            ['|', [this.state.forecastField, '=', false],
             [this.state.forecastField, '>=', this.state.forecastStart]
            ];
    }

    /**
     * The state is mostly dependent on 2 context keys :
     * forecast_field -> is a prerequisite for this extension to work
     * forecast_filter -> a filter which applies this context key should be present and active in
     * order to get the modified domain
     * If the forecast_field is present in the groupby, the related granularity is used
     * If no granularity is specified, or if there is no groupby, the default is "month"
     * If there is a groupby, but not the forecast_field, "day" is used (the filter will get data
     * from 00:00:00 today, browser time)
     *
     * @private
     */
    _computeState() {
        this.prepareState();
        if (!this.config.context.forecast_field) { return; }
        this.state.forecastField = this.config.context.forecast_field;
        const format = DATE_FORMAT[this.config.fields[this.state.forecastField].type];
        const filters = this.config.get('filters').flat();
        this.state.forecastFilter = !!filters.filter(f => f.isActive && f.context &&
            f.context.forecast_filter).length;
        const groupBy = this.config.get('groupBy').flat();
        const forecastGroupBys = groupBy.filter(gb => gb.includes(this.state.forecastField));
        let granularity = "month";
        if (forecastGroupBys.length > 0) {
            [this.state.forecastField, granularity] = [...forecastGroupBys[0].split(":"), granularity];
        } else if (groupBy.length) {
            // there is a groupBy, but it is not the forecast_field
            granularity = "day";
        }
        let startMoment = moment().startOf(granularity);
        // The server needs a date/time in UTC, but to avoid a day shift in case
        // of date, we only need to consider it for datetime fields
        if (this.config.fields[this.state.forecastField].type === "datetime") {
            startMoment = moment.utc(startMoment);
        }
        this.state.forecastStart = startMoment.format(format);
    }
}

ActionModel.registry.add("Forecast", ForecastModelExtension, 20);

export default ForecastModelExtension;
