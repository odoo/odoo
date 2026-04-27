/** @odoo-module **/

import { pivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");


export class RecruitmentReportPivotController extends pivotView.Controller {

    /**
     * @param {CustomEvent} ev
     */
    onOpenView(cell) {
        if (cell.value === undefined || this.model.metaData.disableLinking) {
            return;
        }

        const context = Object.assign({}, this.model.searchParams.context);
        Object.keys(context).forEach((x) => {
            if (x === "group_by" || x.startsWith("search_default_")) {
                delete context[x];
            }
        });

        // retrieve form and list view ids from the action
        const { views = [] } = this.env.config;
        this.views = ["list", "form"].map((viewType) => {
            const view = views.find((view) => view[1] === viewType);
            return [view ? view[0] : false, viewType];
        });

        const group = {
            rowValues: cell.groupId[0],
            colValues: cell.groupId[1],
            originIndex: cell.originIndexes[0],
        };

        const domain = this.model.getGroupDomain(group);
        if (cell.measure == "hired") {
            domain.unshift("&");
            domain.push(['hired', '=', true]);
        }
        if (cell.measure == "refused") {
            domain.unshift("&");
            domain.push(['refused', '=', true]);
        }
        this.openView(domain, this.views, context);
    }
}

viewRegistry.add("recruitment_report_pivot", {
    ...pivotView,
    Controller: RecruitmentReportPivotController,
});
