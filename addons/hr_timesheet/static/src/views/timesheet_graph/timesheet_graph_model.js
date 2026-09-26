import { _t } from "@web/core/l10n/translation";
import { GraphModel } from "@web/views/graph/graph_model";

import { patchGraphModel } from "../graph_model_patch";

export class hrTimesheetGraphModel extends GraphModel {
    /**
     * Make the line overlaying stacked bars show the average instead of their sum.
     * @override
     */
    _getLineOverlayDataset() {
        const lineOverlayDataset = super._getLineOverlayDataset();
        if (lineOverlayDataset) {
            const datasets = this.data.datasets;
            lineOverlayDataset.label = _t("Average");
            lineOverlayDataset.data = lineOverlayDataset.data.map((sum, index) => {
                const count = datasets.filter((dataset) => dataset.data[index]).length;
                return count ? sum / count : 0;
            });
        }
        return lineOverlayDataset;
    }
}
patchGraphModel(hrTimesheetGraphModel);
