/** @odoo-module **/

import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { groupBy } from "@web/core/utils/arrays";


export class HrHolidaysGraphRenderer extends GraphRenderer {
    getBarChartData() {
        let data = super.getBarChartData();
        for (let index = 0; index < data.datasets.length; ++index) {
            const dataset = data.datasets[index];
            let stack = "";
            if (this._isLeaveTypeInLabel(dataset.label, 'Allocation')){
                stack = "Allocation";
            }
            else if (this._isLeaveTypeInLabel(dataset.label, 'Time Off')){
                stack = "Time Off";
            }
            dataset.stack = stack;
        }

        // Balance represents the leave balance = Allocation - Time Off.
        let balanceDatasets = this._computeBalanceDatasets(data);
        data.datasets.push(...balanceDatasets);
        this._convertTimeOffDataToPositive(data.datasets.filter(dataset => dataset.stack === 'Time Off'));
        return data;
    }

    _computeBalanceDatasets(data) {
        let balanceDatasets = [];
        /*
        If a dataset has the label `Mitchell Admin / Time Off` and another dataset
        has the label `Mitchell Admin / Allocation`, then we need to group both these
        datasets under the label `Mitchell Admin / Balance`.
        */
        const datasetsByLabel = groupBy(data.datasets, (dataset) => this._replaceLeaveTypeWithBalance(dataset.label, dataset.stack));
        for (const [label, datasets] of Object.entries(datasetsByLabel)) {
            let balanceDataset = this._initializeBalanceDatasetFrom(datasets[0], label);
            balanceDataset.data = this._computeBalanceData(datasets);
            balanceDatasets.push(balanceDataset);
        }
        return balanceDatasets;
    }

    _initializeBalanceDatasetFrom(dataset, label){
        let balanceDataset = {}
        balanceDataset.trueLabels = dataset.trueLabels;
        balanceDataset.stack = "Balance";
        balanceDataset.originIndex = dataset.originIndex
        balanceDataset.label = label;

        balanceDataset.domains = this._removeLeaveTypeFromDomains(dataset.domains);
        balanceDataset.identifiers = this._removeLeaveTypeFromIdentifiers(dataset.identifiers);

        balanceDataset.backgroundColor = dataset.backgroundColor;
        balanceDataset.borderRadius = dataset.borderRadius;
        balanceDataset.cumulatedStart = dataset.cumulatedStart;
        return balanceDataset;
    }

    _removeLeaveTypeFromDomains(domains){
        /* 
        If a domain includes ['leave_type', '=', 'allocation'] or ['leave_type', '=', 'request'], it will be
        replaced by ['leave_type', 'in', ['allocation', 'request']] because the balanceDataset includes both `Allocation`
        and `Time Off` records.
        */
        let domainsWithoutLeaveType = JSON.parse(JSON.stringify(domains));
        for (const domain of domainsWithoutLeaveType){
            for (let i = 0; i < domain.length; i++){
                if (domain[i][0] === 'leave_type'){
                    domain[i] = ['leave_type', 'in', ['allocation', 'request']];
                }
            }
        }
        return domainsWithoutLeaveType;
    }

    _removeLeaveTypeFromIdentifiers(identifiers){
        /* 
        Remove {"leave_type":"allocation"} and {"leave_type":"request"} from identifiers.
        So for example the identifier "[{"employee_id":[1,"Mitchell Admin"]},{"holiday_status_id":[1,"Paid Time Off"]},{"leave_type":"allocation"}]"
        becomes "[{"employee_id":[1,"Mitchell Admin"]},{"holiday_status_id":[1,"Paid Time Off"]}]"
        */
        let identifiersWithoutLeaveType = new Set()
        for (const identifier of identifiers){
            /*
             Each identifier (after parsing) is a list of objects. We want to remove the object {"leave_type":"allocation"}
             or {"leave_type":"request"} depending on which one is present.
             */
            let identifierObjects = JSON.parse(identifier);
            let leaveTypeIndex = -1;
            for(let i = 0; i < identifierObjects.length; i++){
                if (identifierObjects[i].hasOwnProperty('leave_type')){
                    leaveTypeIndex = i;
                    break;
                }
            }
            if (leaveTypeIndex != -1){
                identifierObjects.splice(leaveTypeIndex, 1);
            }
            identifiersWithoutLeaveType.add(JSON.stringify(identifierObjects));
        }
        return identifiersWithoutLeaveType;
    }

    _computeBalanceData(datasets){
        let data = new Array(datasets[0].trueLabels.length).fill(0);
        for (const dataset of datasets){
            for (let i = 0; i < dataset.data.length; i++){
                data[i] += dataset.data[i];
            }
        }
        return data;
    }

    _convertTimeOffDataToPositive(timeoffDatasets){
        for (const dataset of timeoffDatasets){
            dataset.data = dataset.data.map(datapoint => - datapoint);
        }
    }

    _isLeaveTypeInLabel(label, leaveType){
        const pattern = this._createLeaveTypePattern(leaveType);
        return pattern.test(label);
    }

    _replaceLeaveTypeWithBalance(label, leaveType) {
        const pattern = this._createLeaveTypePattern(leaveType);
        return label.replace(pattern, (match, prefix, leave_type, suffix) => {
            return (prefix || '') + 'Balance' + (suffix || '');
        });
    }

    _createLeaveTypePattern(leaveType){
        /*
        The label could be `Time Off`, `Paid Time Off / Time Off`, 
        `Time Off / Paid Time Off`, or `Mitchell Admin / Time Off / Paid Time Off`.
        So this pattern matches : `leave_type`, `/ leave_type`, `leave_type /` or `/ leave_type /`.
        leaveType is either `Allocation` or `Time Off`.
        */
        return new RegExp(`(\\/ |^)(${leaveType})( \\/)?`);
    }
}
