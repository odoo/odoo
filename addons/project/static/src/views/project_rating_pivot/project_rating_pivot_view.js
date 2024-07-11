/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { PivotArchParser } from "@web/views/pivot/pivot_arch_parser";
import { pivotView } from "@web/views/pivot/pivot_view";

const viewRegistry = registry.category("views");

const MEASURE_STRINGS = {
    parent_res_id: _t("Project"),
    rating: _t("Rating Value (/5)"),
    res_id: _t("Task"),
};

class ProjectRatingArchParser extends PivotArchParser {
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

const projectRatingPivotView = {
    ...pivotView,
    ArchParser: ProjectRatingArchParser,
};

viewRegistry.add("project_rating_pivot", projectRatingPivotView);
