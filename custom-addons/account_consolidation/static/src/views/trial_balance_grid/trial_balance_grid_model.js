/** @odoo-module */

import { GridModel, GridCell, GridDataPoint } from "@web_grid/views/grid_model";

export class ConsolidationGridCell extends GridCell {
    get readonly() {
        return super.readonly || this.column.cells.some((c) => c._readonly);
    }
}

export class ConsolidationGridDataPoint extends GridDataPoint {
    async _searchMany2oneColumns(domain, readonlyField) {
        const filterDomain = domain || [];
        const { default_period_id } = this.searchParams.context;
        if (this.columnFieldName === "journal_id" && default_period_id) {
            filterDomain.push(["period_id", "=", default_period_id]);
        }
        return await super._searchMany2oneColumns(filterDomain, "auto_generated");
    }
}

export class ConsolidationGridModel extends GridModel {
    static Cell = ConsolidationGridCell;
    static DataPoint = ConsolidationGridDataPoint;
}
