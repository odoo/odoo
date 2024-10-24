/** @odoo-module **/

import { GraphModel } from "@web/views/graph/graph_model";
import { sortBy } from "@web/core/utils/arrays";

export class HrHolidaysGraphModel extends GraphModel {
    async load(searchParams) {
        // If groupBy is empty, then we should fallback to the default groupBy instead of adding `leave_type`.
        // That is the reason for the condition searchParams.groupBy.length != 0.
        if (searchParams.groupBy.length != 0 && !searchParams.groupBy.includes('leave_type')){
            searchParams.groupBy.push('leave_type');
        }
        await super.load(...arguments)
    }

    _getLineOverlayDataset() {
        // Given that there are at least 2 stack one for allocation and one for time off
        // then there shouldn't be a lineOverlay. 
        return null;
    }

    /**
     * Eventually filters and sort data points.
     * @protected
     * @returns {Object[]}
     */
    _getProcessedDataPoints() {
        //
        const { domains, groupBy, mode, order } = this.metaData;
        let processedDataPoints = [];
        if (mode === "bar") {
            processedDataPoints = this.dataPoints.filter((dataPoint) => dataPoint.count !== 0);
            if (order !== null && domains.length === 1 && groupBy.length > 0) {
                // group data by their x-axis value, and then sort datapoints
                // based on the balance = Allocation - Time Off in ascending/descending order
                const groupedDataPoints = {};
                for (const dataPt of processedDataPoints) {
                    const key = dataPt.labels[0]; // = x-axis value under the current assumptions
                    if (!groupedDataPoints[key]) {
                        groupedDataPoints[key] = [];
                    }
                    groupedDataPoints[key].push(dataPt);
                }
                const groups = Object.values(groupedDataPoints);
                const groupTotal = (group) => group.reduce((sum, dataPt) => sum + dataPt.value, 0);
                processedDataPoints = sortBy(groups, groupTotal, order.toLowerCase()).flat();
            }
        }
        else {
            processedDataPoints = super._getProcessedDataPoints();
        }
        return processedDataPoints;
    }
}
