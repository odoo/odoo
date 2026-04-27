/** @odoo-module **/

import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { graphView } from "@web/views/graph/graph_view";
import { registry } from "@web/core/registry";

export class RecruitmentGraphRenderer extends GraphRenderer {
    getScaleOptions() {
        const scaleOptions = super.getScaleOptions();

        if ('yAxes' in scaleOptions) {
            scaleOptions.yAxes.suggestedMax = 7;
        }

        return scaleOptions;
    }
}

registry.category("views").add('recruitment_report_view_graph', {
    ...graphView,
    Renderer: RecruitmentGraphRenderer,
});

