/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { SearchModel } from "@web/search/search_model";
import { useService } from "@web/core/utils/hooks";

/**
 * This is the conversion of ForecastModelExtension. See there for more
 * explanations of what is done here.
 */

export class ForecastSearchModel extends SearchModel {
    setup() {
        super.setup(...arguments);
        this.fillTemporalService = useService("fillTemporalService");
        this.hideTemporalFilter = false;
        this._dynamicTemporalEnd = false;
    }
    async load() {
        await super.load(...arguments);
        this.updateTemporalFilter();
    }
    /**
     * Force the end of the period to some date
     * updates _dynamicTemporalEnd
     * @param {DateTime} end
     */
    setTemporalEnd(end) {
        const temporal = this.fillTemporalService();
        if (end != temporal.end) {
            this._dynamicTemporalEnd = end;
            temporal.setEnd(end);
        }
    }
    unsetTemporalEnd() {
        const temporal = this.fillTemporalPeriod();
        if (!temporal.computedEnd) {
            temporal._computeEnd();
            this._dynamicTemporalEnd = false;
        }
    }
    expandTemporalFilter() {
        this.fillTemporalPeriod().expand();
        this.updateTemporalFilter();
    }
    _updateTemporalFilterPreHook() {
        if (this._dynamicTemporalEnd) {
            this.setTemporalEnd(this._dynamicTemporalEnd);
        }
    }
    updateTemporalFilter(forceFillingTo = undefined) {
        this._updateTemporalFilterPreHook();
        const domain = this.fillTemporalPeriod().getDomain({ domain: [] });
        const context = this.fillTemporalPeriod().getContext({
            context: {},
            forceFillingTo: forceFillingTo,
        });
        this.setTemporalFilter(domain, context);
    }
    setTemporalFilter(domain, context) {
        this.disableTemporalFilters();
        const filters = this._getTemporalFilters();
        if (filters.length) {
            filters[0].crmTemporalFilter = true;
            filters[0].domain = domain;
            filters[0].context = context;
            this.toggleSearchItem(filters[0].id);
        } else {
            this.createNewFilters([
                {
                    crmTemporalFilter: true,
                    context: context,
                    description: _t("CRM Forecast Temporal Filter"),
                    domain: domain,
                    type: "filter",
                },
            ]);
        }
    }
    _getTemporalFilters() {
        return Object.values(this.searchItems).filter(
            (searchItem) =>
                searchItem.crmTemporalFilter ||
                ("context" in searchItem && searchItem.context.includes("forecast_filter")),
        );
    }
    _getActiveTemporalFilters() {
        const filters = this._getTemporalFilters();
        return filters
            .filter((filter) => {
                return this.query?.some((queryElem) => queryElem.searchItemId === filter.id);
            })
            .map((filter) => filter.id);
    }
    isTemporalFilterEnabled() {
        return !!this._getActiveTemporalFilters();
    }
    /**
     * Disable the filter(s).
     * Intended to be used when removing grouping or switching views.
     */
    disableTemporalFilters() {
        for (const filterId of this._getActiveTemporalFilters()) {
            this.toggleSearchItem(filterId);
        }
    }
    /**
     * @override
     */
    exportState() {
        this.disableTemporalFilters();
        const state = super.exportState();
        state.forecast = {
            forecastEnd: this.forecastStart,
        };
        return state;
    }

    /**
     * @override
     */
    _importState(state) {
        super._importState(...arguments);
        if (state.forecast) {
            this._dynamicTemporalEnd = state.forecast.forecastStart;
        }
    }

    /**
     * @override
     */
    _reset() {
        super._reset();
        this.forecastStart = null;
    }

    /**
     * @returns {FillTemporalPeriod} current fillTemporalPeriod according to group by state
     */
    fillTemporalPeriod() {
        const minGroups =
            (this.context.fill_temporal && this.context.fill_temporal.min_groups) || undefined;

        const [groupByFieldName, granularity] = this.groupBy?.length
            ? this.groupBy[0].split(":")
            : [this.context.forecast_field, "month"];
        const groupByField = this.searchViewFields[groupByFieldName];
        const { name, type } = groupByField;

        return this.fillTemporalService.getFillTemporalPeriod({
            modelName: this.resModel,
            field: {
                name,
                type,
            },
            granularity: granularity || "month",
            minGroups,
        });
    }

    /**
     * @override
     * @returns {Array} copy of parent value with temporal filter removed
     */
    _getFacets() {
        let facets = super._getFacets(...arguments);
        if (!this.hideTemporalFilter) {
            return facets;
        }
        for (const group of this._getGroups()) {
            for (const searchItemId of group.activeItems.map((item) => item.searchItemId)) {
                if (searchItemId && this.searchItems[searchItemId].crmTemporalFilter) {
                    facets = facets.filter((facet) => facet.groupId !== group.id);
                    continue;
                }
            }
        }
        return facets;
    }
}
