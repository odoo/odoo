/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { makeContext } from "@web/core/context";
import { SearchModel } from "@web/search/search_model";
import {
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";

/**
 * This is the conversion of ForecastModelExtension. See there for more
 * explanations of what is done here.
 */

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
            const groupBy = this.groupBy;
            const firstForecastGroupBy = groupBy.find((gb) => gb.includes(forecastField));
            let granularity = "month";
            if (firstForecastGroupBy) {
                granularity = firstForecastGroupBy.split(":")[1] || "month";
            } else if (groupBy.length) {
                granularity = "day";
            }
            const startDateTime = luxon.DateTime.now().startOf(granularity);
            this.forecastStart = type === "datetime" ? serializeDateTime(startDateTime) : serializeDate(startDateTime);
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
