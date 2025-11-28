import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { loadFrequency } from "../aw_local_config";

export class FrequencyViewer extends Component {
    setup() {
        this.freq = loadFrequency();
    }

    getRowStats(rowTitle) {
        const combos = this.freq[rowTitle] || {};

        return Object.entries(combos)
            .map(([jsonKey, count]) => {
                const parsed = JSON.parse(jsonKey);
                return { ...parsed, count };
            })
            .sort((a, b) => b.count - a.count);
    }
}

FrequencyViewer.template = "hr_timesheet.FrequencyViewer";

registry.category("actions").add("frequency_viewer", FrequencyViewer);
