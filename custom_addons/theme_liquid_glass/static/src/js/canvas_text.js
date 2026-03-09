/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { GraphRenderer } from "@web/views/graph/graph_renderer";

const FONT_COLOR = "#ffffff";

patch(GraphRenderer.prototype, {

    getScaleOptions() {
        const options = super.getScaleOptions();

        if (options.x?.ticks) {
            options.x.ticks.color = FONT_COLOR;
        }
        if (options.x?.title) {
            options.x.title.color = FONT_COLOR;
        }

        if (options.y?.ticks) {
            options.y.ticks.color = FONT_COLOR;
        }
        if (options.y?.title) {
            options.y.title.color = FONT_COLOR;
        }

        return options;
    },

    getLegendOptions() {
        const options = super.getLegendOptions();

        if (options.labels?.generateLabels) {
            const originalGenerateLabels = options.labels.generateLabels;

            options.labels.generateLabels = (chart) => {
                return originalGenerateLabels(chart).map(label => ({
                    ...label,
                    fontColor: FONT_COLOR,
                }));
            };
        }

        return options;
    },

});
