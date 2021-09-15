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
     * @override
     */
    exportState() {
        const state = super.exportState();
        state.forecast = {
            forecastField: this.forecastField,
            forecastFilter: this.forecastFilter,
            forecastStart: this.forecastStart,
        };
        return state;
    }

    /**
     * @protected
     * @returns {string}
     */
    _getForecastStart() {
        /** @todo stop using moment */
        const type = this.searchViewFields[this.forecastField].type;
        let startMoment;
        const groupBy = this.groupBy;
        const firstForecastGroupBy = groupBy.find((gb) => gb.includes(this.forecastField));
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

        const { forecast_field: forecastField } = this.globalContext;
        const searchItem = this.searchItems[activeItem.searchItemId];

        if (forecastField && searchItem.type === "filter") {
            const context = makeContext(searchItem.context || {});
            if (!context.forecast_filter) {
                return domain;
            }

            this.forecastField = forecastField;
            this.forecastFilter = true;
            if (!this.forecastStart) {
                this.forecastStart = this._getForecastStart();
            }

            const forecastDomain = [
                "|",
                [this.forecastField, "=", false],
                [this.forecastField, ">=", this.forecastStart],
            ];
            return Domain.and([domain, forecastDomain]);
        }

        return domain;
    }

    /**
     * @override
     */
    _importState(state) {
        super._importState(...arguments);
        if (state.Forecast) {
            const { forecastField, forecastFilter, forecastStart } = state.forecast;
            this.forecastField = forecastField;
            this.forecastFilter = forecastFilter;
            this.forecastStart = forecastStart;
        }
    }

    /**
     * @override
     */
    _reset() {
        super._reset();
        this.forecastField = null;
        this.forecastFilter = false;
        this.forecastStart = null;
    }
}
