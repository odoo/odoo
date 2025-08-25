/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

import { cookie } from "@web/core/browser/cookie";
import { getColor } from "@web/core/colors/colors";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { groupBy } from "@web/core/utils/arrays";

const colorScheme = cookie.get("color_scheme");


export class HrHolidaysGraphRenderer extends GraphRenderer {
    delimiter = ' / ';

    getBarChartData() {

        let data = super.getBarChartData();
        for (let index = 0; index < data.datasets.length; ++index) {
            const dataset = data.datasets[index];
            // dataset.label takes the form 'Mitchell Admin / Paid Time Off / Allocation'.
            if (dataset.label.split(this.delimiter).includes(this.model.allocation_label)){
                dataset.stack = this.model.allocation_label;
            }
            else if (dataset.label.split(this.delimiter).includes(this.model.timeoff_label)){
                dataset.stack = this.model.timeoff_label;
            }
        }

        if (!(data.datasets.every(dataset => dataset.stack === this.model.allocation_label)
            || data.datasets.every(dataset => dataset.stack === this.model.timeoff_label))){
            let balanceDatasets = this._computeBalanceDatasets(data);
            data.datasets.push(...balanceDatasets);
        }

        // Change time off data to +ve values to be better visualized in the graph view.
        for (let dataset of data.datasets.filter(dataset => dataset.stack === this.model.timeoff_label)){
            dataset.data = dataset.data.map(datapoint => -datapoint);
        }
        return data;
    }

    _computeBalanceDatasets(data) {
        this.balance_label = _t('Balance')
        const datasetsByLabel = groupBy(data.datasets, 
            (dataset) => dataset.label.split(this.delimiter)
            .map(labelPart => labelPart === this.model.allocation_label || labelPart === this.model.timeoff_label ? this.balance_label : labelPart)
            .join(this.delimiter)
        );
        this.datasets_offset = data.datasets.length;
        this.datasets_length = this.datasets_offset + Object.keys(datasetsByLabel).length;
        const balanceDatasets = Object.entries(datasetsByLabel).map(([label, datasets], index) =>
            this._initializeBalanceDatasetFrom(datasets, label, index)
        );
        return balanceDatasets;
    }

    _initializeBalanceDatasetFrom(datasets, label, index){
        let dataset = datasets[0];

        const dataset_index = this.datasets_offset + index;
        const backgroundColor = getColor(dataset_index, colorScheme, this.datasets_length);

        let balanceDataset = {
            'trueLabels': dataset.trueLabels,
            'stack': this.balance_label,
            'label': label,
            'backgroundColor': backgroundColor,
            'borderRadius': dataset.borderRadius,
            'cumulatedStart': dataset.cumulatedStart,
        };
 
        balanceDataset.domains = dataset.domains.map(domain => 
            domain.map(condition => 
                condition.includes('leave_type')
                ? ['leave_type', 'in', ['allocation', 'request']]
                : condition
            )
        ); 

        /* Because the balanceDataset includes both `Allocation` and `Time Off` records: {"leave_type":"allocation"} and {"leave_type":"request"} are removed from identifiers.
        For example: the identifier "[{"employee_id":[1,"Mitchell Admin"]},{"leave_type":"allocation"}]" becomes "[{"employee_id":[1,"Mitchell Admin"]}]" */
        balanceDataset.identifiers = new Set([...dataset.identifiers].map(identifier => 
                JSON.stringify( 
                    JSON.parse(identifier) // The output is an array of objects.
                    .filter(identifierObject => !identifierObject.hasOwnProperty('leave_type'))
                )
            )
        );

        balanceDataset.data = new Array(balanceDataset.trueLabels.length).fill(0);
        const allocation_datasets = datasets.filter(dataset => dataset.stack === this.model.allocation_label)
        for (let allocation_dataset of allocation_datasets){
            for (let i = 0; i < allocation_dataset.data.length; i++){
                balanceDataset.data[i] += allocation_dataset.data[i];
            }
        }
        const timeoff_datasets = datasets.filter(dataset => dataset.stack === this.model.timeoff_label)
        for (let timeoff_dataset of timeoff_datasets){
            for (let i = 0; i < timeoff_dataset.data.length; i++){
                if (balanceDataset.data[i] != 0)
                    balanceDataset.data[i] += timeoff_dataset.data[i];
            }
        }
        return balanceDataset;
    }
}
