/** @odoo-module */

import ActionModel from "web.ActionModel";
import ControlPanelModelExtension from "web/static/src/js/control_panel/control_panel_model_extension.js";
import { Domain } from "@web/core/domain";
import { makeContext } from "@web/core/context";

/**
 * This files defines an extension of @see ControlPanelModelExtension.
 * That extension specifies how forecast filters behave.
 *
 * A forecast filter is a filter that has a context containing a special key
 * "forecast_filter" with value the name of a date/datetime field, e.g.
 *
 * <filter name="foo" string="Foo" context={'forecast_filter': 'date_field} />
 *
 * The domain of a forecast filter has a dynamic domain of the form
 *
 * ['&', ['date_field', '=', false], ['date_field', '>=', forecastStart]]
 *
 * where forecastStart is a date/datetime that depends on the active groupbys.
 * The rough idea is to filter records for which the 'date_field' value is in
 * the current "period" or in the future, where the current period is defined by
 * some granularity, e.g. "month".
 *
 * For example, if the only groupby activated is 'date_field' and today is
 * 2021-04-21, the domain of the above forecast filter will be
 *
 * ['&', ['date_field', '=', false], ['date_field', '>=', '2021-04-01']]
 */
const DATE_FORMAT = {
    datetime: "YYYY-MM-DD HH:mm:ss",
    date: "YYYY-MM-DD",
};
class ForecastModelExtension extends ControlPanelModelExtension {
    /**
     * Returns a date (datetime) starting from a "forecast" field of type date (resp. datetime).
     * The value returned depends on the active groubys.
     * @private
     * @param {string} forecastField the name of a date/datetime field
     * @returns {string}
     */
    _getForecastStart(forecastField) {
        const type = this.config.fields[forecastField].type;
        let startMoment;
        const groupBy = this.config.get("groupBy");
        const firstForecastGroupBy = groupBy.find((gb) => gb.includes(forecastField));
        let granularity = "month";
        if (firstForecastGroupBy) {
            granularity = firstForecastGroupBy.split(":")[1] || "month";
        } else if (groupBy.length) {
            granularity = "day";
        }
        startMoment = moment().startOf(granularity);
        if (type === "datetime") {
            startMoment = moment.utc(startMoment);
        }
        const format = DATE_FORMAT[type];
        return startMoment.format(format);
    }

    /**
     * @override
     */
    _getFilterDomain(filter) {
        const domain = super._getFilterDomain(...arguments);

        if (filter.type === "filter") {
            const context = makeContext(filter.context || {});
            if (!context.forecast_field) {
                return domain;
            }

            const forecastField = context.forecast_field;
            const forecastStart = this._getForecastStart(forecastField);

            const forecastDomain = new Domain([
                "|",
                [forecastField, "=", false],
                [forecastField, ">=", forecastStart],
            ]);
            return forecastDomain.toString();
        }

        return domain;
    }
}

ActionModel.registry.add("forecast", ForecastModelExtension, 20);
