import { globalFiltersFieldMatchers } from "@spreadsheet/global_filters/plugins/global_filters_core_plugin";

import { AbstractFigureClipboardHandler, registries } from "@odoo/o-spreadsheet";

const { clipboardHandlersRegistries } = registries;

class OdooChartFieldMatchingClipboardHandler extends AbstractFigureClipboardHandler {
    copy({ figureId }) {
        if (!this.getters.getChart(figureId)?.type.startsWith("odoo")) {
            return;
        }
        return {
            odooChartFieldMatching: this.getters.getChartFieldMatch(figureId),
        };
    }

    paste(target, clippedContent, options) {
        const { figureId: newFigureId } = target;
        const clippedMatchings = clippedContent.odooChartFieldMatching;
        if (!clippedMatchings) {
            return;
        }

        const odooChartIds = globalFiltersFieldMatchers["chart"].getIds();
        for (const filterId in clippedMatchings) {
            const copiedFieldMatching = clippedMatchings[filterId];
            const filter = this.getters.getGlobalFilter(filterId);
            const currentChartMatchings = {};
            // copy existing matching of other chars for this filter
            for (const chartId of odooChartIds) {
                currentChartMatchings[chartId] = this.getters.getOdooChartFieldMatching(
                    chartId,
                    filterId
                );
            }
            if (options?.isCutOperation) {
                delete currentChartMatchings[clippedContent.figureId];
            }
            if (copiedFieldMatching.chain === currentChartMatchings[newFigureId]?.chain) {
                // avoid dispatching a command if the automatic field matching already set
                // the same matching
                continue;
            }
            currentChartMatchings[newFigureId] = copiedFieldMatching;
            this.dispatch("EDIT_GLOBAL_FILTER", {
                filter,
                chart: currentChartMatchings,
            });
        }
    }
}

clipboardHandlersRegistries.figureHandlers.add(
    "odoo_chart_field_matching",
    OdooChartFieldMatchingClipboardHandler
);
