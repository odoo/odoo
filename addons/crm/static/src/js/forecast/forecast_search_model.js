/** @odoo-module */

import { Domain } from "@web/core/domain";
import { makeContext } from "@web/core/context";
import { SearchModel } from "@web/search/search_model";

/**
 * This is the conversion of ForecastModelExtension. See there for more
 * explanations of what is done here.
 */
const DATE_FORMAT = {
    datetime: "YYYY-MM-DD HH:mm:ss",
    date: "YYYY-MM-DD",
};

export class ForecastSearchModel extends SearchModel {
    /**
     * @protected
     * @param {string} forecastField name of the date/time field related to the forecast
     * @returns {string}
     */
    _getForecastStart(forecastField) {
        /** @todo stop using moment */
        const type = this.searchViewFields[forecastField].type;
        let startMoment;
        const groupBy = this.groupBy;
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

    _getSearchItemDomain(activeItem) {
        const domain = super._getSearchItemDomain(...arguments);
        const searchItem = this.searchItems[activeItem.searchItemId];

        if (searchItem.type === "filter") {
            const context = makeContext(searchItem.context || {});
            if (!context.forecast_field) {
                return domain;
            }

            const forecastField = context.forecast_field;
            const forecastStart = this._getForecastStart(forecastField);

            const forecastDomain = [
                "|",
                [forecastField, "=", false],
                [forecastField, ">=", forecastStart],
            ];
            return Domain.and([domain, forecastDomain]);
        }

        return domain;
    }
}
