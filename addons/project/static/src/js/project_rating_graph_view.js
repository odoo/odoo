/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { GraphView } from "@web/views/graph/graph_view";
import { GraphArchParser } from "@web/views/graph/graph_arch_parser";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

const MEASURE_STRINGS = {
    parent_res_id: _lt("Project"),
    rating: _lt("Rating Value (/5)"),
    res_id: _lt("Task"),
};

class ProjectRatingArchParser extends GraphArchParser {
    parse() {
        const archInfo = super.parse(...arguments);
        for (const [key, val] of Object.entries(MEASURE_STRINGS)) {
            archInfo.fieldAttrs[key] = {
                ...archInfo.fieldAttrs[key],
                string: val.toString(),
            };
        }
        return archInfo;
    }
}

// Would it be not better achiedved by using a proper arch directly?

class ProjectRatingGraphView extends GraphView {}
ProjectRatingGraphView.archParser = ProjectRatingArchParser;

viewRegistry.add("project_rating_graph", ProjectRatingGraphView);
