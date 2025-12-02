import { _t } from "@web/core/l10n/translation";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { getBestGranularity, getValidGranularities } from "../../global_filters/helpers";

export class OdooChartFeaturePlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ (["getAvailableChartGranularities"]);

    overwrittenGranularities = {};
    granularityOptionsCache = {};

    handle(cmd) {
        switch (cmd.type) {
            case "SET_GLOBAL_FILTER_VALUE": {
                if (this.getters.isDashboard()) {
                    this._onGlobalFilterChange(cmd);
                }
                break;
            }
            case "UPDATE_CHART_GRANULARITY": {
                this._updateChartGranularity(cmd.chartId, cmd.granularity);
                this.overwrittenGranularities[cmd.chartId] = cmd.granularity;
                break;
            }
        }
    }

    getAvailableChartGranularities(chartId) {
        if (this.granularityOptionsCache[chartId]) {
            return this.granularityOptionsCache[chartId];
        }
        const { granularity, fieldName } = this.getters.getChartGranularity(chartId);
        if (!granularity) {
            return [];
        }
        const allGranularities = [
            { value: "hour", label: _t("Hours") },
            { value: "day", label: _t("Days") },
            { value: "week", label: _t("Weeks") },
            { value: "month", label: _t("Months") },
            { value: "quarter", label: _t("Quarters") },
            { value: "year", label: _t("Years") },
        ];
        const filterId = this._getChartHorizontalAxisFilter(chartId, fieldName);
        const matching = this.getters.getOdooChartFieldMatching(chartId, filterId);
        if (matching?.type !== "datetime") {
            allGranularities.shift();
        }
        const currentFilterValue = filterId
            ? this.getters.getGlobalFilterValue(filterId)
            : undefined;
        const allowed = getValidGranularities(currentFilterValue);
        const available = allGranularities.filter(({ value }) => allowed.includes(value));

        this.granularityOptionsCache[chartId] = available;
        return available;
    }

    _onGlobalFilterChange(cmd) {
        const filterId = cmd.id;
        const globalFilter = this.getters.getGlobalFilter(filterId);
        if (globalFilter.type !== "date") {
            return;
        }
        for (const chartId of this.getters.getOdooChartIds()) {
            const { fieldName, granularity: currentGranularity } =
                this.getters.getChartGranularity(chartId);
            const fieldMatching = this.getters.getChartFieldMatch(chartId)[filterId];
            const bestGranularity = getBestGranularity(cmd.value, fieldMatching);
            const validGranularities = getValidGranularities(cmd.value);
            const shouldAutoUpdate =
                fieldMatching?.chain === fieldName &&
                !validGranularities.includes(this.overwrittenGranularities[chartId]) &&
                bestGranularity !== currentGranularity;

            if (shouldAutoUpdate) {
                this.dispatch("UPDATE_CHART_GRANULARITY", {
                    chartId,
                    granularity: bestGranularity,
                });
                this.overwrittenGranularities[chartId] = undefined;
            }
            if (currentGranularity) {
                this.granularityOptionsCache[chartId] = undefined;
            }
        }
    }

    _updateChartGranularity(chartId, granularity) {
        const definition = this.getters.getChartDefinition(chartId);
        const { fieldName } = this.getters.getChartGranularity(chartId);
        const newGroupBy = [
            `${fieldName}:${granularity}`,
            ...definition.searchParams.groupBy.slice(1),
        ];
        this.dispatch("UPDATE_CHART", {
            chartId,
            figureId: this.getters.getFigureIdFromChartId(chartId),
            definition: {
                ...definition,
                // I don't know why it's in both searchParams and metaData.
                searchParams: {
                    ...definition.searchParams,
                    groupBy: newGroupBy,
                },
                metaData: {
                    ...definition.metaData,
                    groupBy: newGroupBy,
                },
            },
        });
    }

    _getChartHorizontalAxisFilter(chartId, fieldName) {
        for (const filter of this.getters.getGlobalFilters()) {
            const matching = this.getters.getOdooChartFieldMatching(chartId, filter.id);
            if (matching?.chain === fieldName) {
                return filter.id;
            }
        }
        return undefined;
    }
}
