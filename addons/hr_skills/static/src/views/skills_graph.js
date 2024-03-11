/** @odoo-module **/

import { registry } from "@web/core/registry";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { graphView } from "@web/views/graph/graph_view";

export class SkillsGraphRenderer extends GraphRenderer {
    getScaleOptions() {
        const scaleOptions = super.getScaleOptions();

        if ('yAxes' in scaleOptions) {
            scaleOptions['yAxes'][0]['ticks']['suggestedMax'] = 100;
        }

        return scaleOptions;
    }
}

export const skillsGraphView = {
    ...graphView,
    Renderer: SkillsGraphRenderer,
};

registry.category("views").add("skills_graph", skillsGraphView);
