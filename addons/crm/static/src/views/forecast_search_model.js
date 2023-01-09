/** @odoo-module **/

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
     * @override
     */
    exportState() {
        const state = super.exportState();
        state.forecast = {
            forecastStart: this.forecastStart,
        };
        return state;
    }

    /**
     * @override
     */
    _getDomain(params = {}) {
        const domain = super._getDomain(...arguments);
        const forecastField = this.globalContext.forecast_field;
        if (!forecastField) {
            return domain;
        }
        let forecastFilter = false;
        for (const queryElem of this.query) {
            const searchItem = this.searchItems[queryElem.searchItemId];
            if (searchItem.type === "filter") {
                const context = makeContext([searchItem.context || {}]);
                if (context.forecast_filter) {
                    forecastFilter = true;
                    break;
                }
            }
        }
        if (!forecastFilter) {
            return domain;
        }
        const forecastStart = this._getForecastStart(forecastField);
        const forecastDomain = [
            "|",
            [forecastField, "=", false],
            [forecastField, ">=", forecastStart],
        ];
        const fullDomain = Domain.and([domain, forecastDomain]);
        return params.raw ? fullDomain : fullDomain.toList();
    }

    /**
     * @protected
     * @param {string} forecastField
     * @returns {string}
     */
    _getForecastStart(forecastField) {
        if (!this.forecastStart) {
            /** @todo stop using moment */
            const { type } = this.searchViewFields[forecastField];
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
            this.forecastStart = startMoment.format(format);
        }
        return this.forecastStart;
    }

    /**
     * @override
     */
    _importState(state) {
        super._importState(...arguments);
        if (state.forecast) {
            this.forecastStart = state.forecast.forecastStart;
        }
    }

    /**
     * @override
     */
    _reset() {
        super._reset();
        this.forecastStart = null;
    }
}
