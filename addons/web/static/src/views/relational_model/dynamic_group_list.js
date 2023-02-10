/* @odoo-module */

import { DynamicList } from "./dynamic_list";

export class DynamicGroupList extends DynamicList {
    setup(params) {
        super.setup(params);
        this.isGrouped = true;
        this.groupBy = params.groupBy;
        const groupByFieldName = this.groupBy[0].split(":")[0];
        this.groupByField = this.fields[groupByFieldName];
        this.groups = params.data.groups.map(
            (g) =>
                new this.model.constructor.Group(this.model, {
                    activeFields: this.activeFields,
                    fields: this.fields,
                    resModel: this.resModel,
                    context: this.context,
                    groupBy: this.groupBy.slice(1),
                    groupByFieldName,
                    data: g,
                })
        );
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    /**
     * List of loaded records inside groups.
     */
    get records() {
        return this.groups
            .filter((group) => !group.isFolded)
            .map((group) => group.records)
            .flat();
    }

    // FIXME: only for list, but makes sense, maybe rename into record_count?
    // count already exists and is the number of groups
    get nbTotalRecords() {
        return this.groups.reduce((acc, group) => acc + group.count, 0);
    }
}
DynamicGroupList.DEFAULT_LOAD_LIMIT = 10; // FIXME: move
