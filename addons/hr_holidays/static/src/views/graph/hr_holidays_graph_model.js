/** @odoo-module **/

import { GraphModel } from "@web/views/graph/graph_model";
import { sortBy } from "@web/core/utils/arrays";

export class HrHolidaysGraphModel extends GraphModel {
    async load(searchParams) {
        if (searchParams.groupBy.length != 0 && !searchParams.groupBy.includes('leave_type')){
            searchParams.groupBy.push('leave_type');
        }
        await super.load(...arguments);
    }

    _getLineOverlayDataset() {
        // Given that there are at least 2 stacks one for allocation and one for time off
        // then there shouldn't be a lineOverlay. 
        return null;
    }

    /**
     * Eventually filters and sort data points.
     * @protected
     * @returns {Object[]}
     */
    _getProcessedDataPoints() {
        const {fields, groupBy, mode, order } = this.metaData;
        this.allocation_label = fields['leave_type'].selection.find((selection) => selection[0] === 'allocation')[1]
        this.timeoff_label = fields['leave_type'].selection.find((selection) => selection[0] === 'request')[1]

        let processedDataPoints = [];
        if (mode === "bar") {
            processedDataPoints = this.dataPoints.filter(
                (dataPoint) => dataPoint.labels[0] !== this._getDefaultFilterLabel(groupBy[0])
            );

            if (order !== null && groupBy.length > 0) {
                const groupedDataPoints = {};
                for (const dataPt of processedDataPoints) {
                    const key = dataPt.labels[0]; // = x-axis value under the current assumptions
                    if (!groupedDataPoints[key]) {
                        groupedDataPoints[key] = [];
                    }
                    groupedDataPoints[key].push(dataPt);
                }

                const groups = Object.values(groupedDataPoints);
                let datapointsWithAllocation = new Set( 
                    groups.flat()
                    .map(dataPoint => {
                        if (dataPoint.labels[dataPoint.labels.length - 1] === this.allocation_label){
                            return dataPoint.labels.slice(0, -1).join('/');
                        }
                        return false;
                    })
                    .filter(label => label !== false)
                )

                const groupTotal = (group) => group.reduce((sum, dataPt) => {
                    if (datapointsWithAllocation.has(dataPt.labels.slice(0, -1).join('/'))){
                        return sum + dataPt.value;
                    }
                    return sum;
                }, 0);

                processedDataPoints = sortBy(groups, groupTotal, order.toLowerCase()).flat();
            } 
            else {
                processedDataPoints = super._getProcessedDataPoints();
            }
            return processedDataPoints;
        }
        return super._getProcessedDataPoints();
    }
}
