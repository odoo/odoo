import { GraphModel } from "@web/views/graph/graph_model";

export class SpreadsheetGraphModel extends GraphModel {
    /**
     * @override
     */
    _filterFinestTimeInterval(groupBy) {
        // the original method only keeps the finest interval option for
        // elements based on date/datetime. We want to keep all the options.
        return groupBy;
    }
}
