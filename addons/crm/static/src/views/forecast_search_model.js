/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { makeContext } from "@web/core/context";
import { SearchModel } from "@web/search/search_model";
<<<<<<< HEAD
import {
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
||||||| parent of cd6adf9a424e (temp)
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
=======
>>>>>>> cd6adf9a424e (temp)

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
    _getSearchItemDomain(activeItem) {
        let domain = super._getSearchItemDomain(activeItem);
        const { searchItemId } = activeItem;
        const searchItem = this.searchItems[searchItemId];
        const context = makeContext([searchItem.context || {}]);
        if (context.forecast_filter) {
            const forecastField = this.globalContext.forecast_field;
            const forecastStart = this._getForecastStart(forecastField);
            const forecastDomain = [
                "|",
                [forecastField, "=", false],
                [forecastField, ">=", forecastStart],
            ];
            domain = Domain.and([domain, forecastDomain]);
        }
        return domain;
    }

    /**
     * @protected
     * @param {string} forecastField
     * @returns {string}
     */
    _getForecastStart(forecastField) {
        if (!this.forecastStart) {
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
            this.forecastStart = startMoment.locale("en").format(format);
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
