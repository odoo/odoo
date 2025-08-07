import { _t } from "@web/core/l10n/translation";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { getBestGranularity, getValidGranularities } from "../../global_filters/helpers";

export class OdooChartFeaturePlugin extends OdooUIPlugin {
    static getters = /** @type {const} */ (["getAvailableChartGranularities"]);

    overwrittenGranularities = {};

    handle(cmd) {
        switch (cmd.type) {
            case "SET_GLOBAL_FILTER_VALUE": {
                if (!this.getters.isDashboard()) {
                    return;
                }
                const filterId = cmd.id;
                const globalFilter = this.getters.getGlobalFilter(filterId);
                if (globalFilter.type === "date") {
                    const charts = this.getters.getOdooChartIds();
                    for (const chartId of charts) {
                        const { fieldName, granularity } =
                            this.getters.getChartGranularity(chartId);
                        const fieldMatching = this.getters.getChartFieldMatch(chartId)[filterId];
                        const bestGranularity = getBestGranularity(cmd.value, fieldMatching);
                        const validGranularities = getValidGranularities(cmd.value);
                        if (
                            fieldMatching?.chain === fieldName &&
                            !validGranularities.includes(this.overwrittenGranularities[chartId]) &&
                            bestGranularity !== granularity
                        ) {
                            this.dispatch("UPDATE_CHART_GRANULARITY", {
                                chartId,
                                granularity: bestGranularity,
                            });
                            this.overwrittenGranularities[chartId] = undefined;
                        }
                    }
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
        const definition = this.getters.getChartDefinition(chartId);
        if (!definition.type.startsWith("odoo_")) {
            return [];
        }
        const { granularity } = this.getters.getChartGranularity(chartId);
        if (!granularity) {
            return [];
        }
        const filterId = this._getChartHorizontalAxisFilter(chartId);
        const currentFilterValue = filterId
            ? this.getters.getGlobalFilterValue(filterId)
            : undefined;
        const all = [
            { value: "day", label: _t("Days") },
            { value: "week", label: _t("Weeks") },
            { value: "month", label: _t("Months") },
            { value: "quarter", label: _t("Quarters") },
            { value: "year", label: _t("Years") },
        ];
        const matching = this.getters.getOdooChartFieldMatching(chartId, filterId);
        if (matching?.type === "datetime") {
            all.unshift({ value: "hour", label: _t("Hours") });
        }
        const validGranularities = getValidGranularities(currentFilterValue);
        return all.filter(
            ({ value }) => validGranularities.includes(value) || value === granularity
        );
    }

    _updateChartGranularity(chartId, granularity) {
        const definition = this.getters.getChartDefinition(chartId);
        const { fieldName } = this.getters.getChartGranularity(chartId);
        this.dispatch("UPDATE_CHART", {
            chartId,
            figureId: this.getters.getFigureIdFromChartId(chartId),
            definition: {
                ...definition,
                // I don't know why it's in both searchParams and metaData.
                searchParams: {
                    ...definition.searchParams,
                    groupBy: [
                        `${fieldName}:${granularity}`,
                        ...definition.searchParams.groupBy.slice(1),
                    ],
                },
                metaData: {
                    ...definition.metaData,
                    groupBy: [
                        `${fieldName}:${granularity}`,
                        ...definition.metaData.groupBy.slice(1),
                    ],
                },
            },
        });
    }

    _getChartHorizontalAxisFilter(chartId) {
        const { fieldName } = this.getters.getChartGranularity(chartId);
        for (const filter of this.getters.getGlobalFilters()) {
            const matching = this.getters.getOdooChartFieldMatching(chartId, filter.id);
            if (matching?.chain === fieldName) {
                return filter.id;
            }
        }
        return undefined;
    }
}
