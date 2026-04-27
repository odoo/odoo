/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { usePlanningModelActions } from "./planning_hooks";

export class PlanningRelationalModel extends RelationalModel {
    /** @override **/
    setup() {
        super.setup(...arguments);
        this.getHighlightIds = usePlanningModelActions({
            getHighlightPlannedIds: () => this.env.searchModel.highlightPlannedIds,
            getContext: () => this.env.searchModel._context,
        }).getHighlightIds;
    }

    /** @override **/
    async load(params = {}) {
        const highlightIds = await this.getHighlightIds();
        if (highlightIds) {
            params.domain = Domain.and([
                params.domain,
                [["id", "in", highlightIds]]
            ]).toList();
        }
        await super.load(...arguments);
    }
}
