/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { formatPercentage } from "@web/views/fields/formatters";
import { registry } from "@web/core/registry";

import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ViewScaleSelector } from "@web/views/view_components/view_scale_selector";
import { download } from "@web/core/network/download";
import { ReportViewMeasures } from "@web/views/view_components/report_view_measures";

const formatters = registry.category("formatters");

export class CohortRenderer extends Component {
    static components = { Dropdown, DropdownItem, ViewScaleSelector, ReportViewMeasures };
    static template = "web_cohort.CohortRenderer";
    static props = ["class", "model", "onRowClicked"];

    setup() {
        this.model = this.props.model;
    }

    range(n) {
        return Array.from({ length: n }, (_, i) => i);
    }

    getFormattedValue(value) {
        const fieldName = this.model.metaData.measure;
        const field = this.model.metaData.measures[fieldName];
        let formatType = this.model.metaData.widgets[fieldName];
        if (!formatType) {
            const fieldType = field.type;
            formatType = ["many2one", "reference"].includes(fieldType) ? "integer" : fieldType;
        }
        const formatter = formatters.get(formatType);
        return formatter(value, field);
    }

    formatPercentage(value) {
        return formatPercentage(value, { digits: [false, 1] });
    }

    getCellTitle(period, measure, count) {
        return _t("Period: %(period)s\n%(measure)s: %(count)s", { period, measure, count });
    }

    get scales() {
        return Object.fromEntries(
            Object.entries(this.model.intervals).map(([s, d]) => [s, { description: d }])
        );
    }

    /**
     * @param {String} scale
     */
    setScale(scale) {
        this.model.updateMetaData({
            interval: scale,
        });
    }

    /**
     * @param {Object} param0
     * @param {string} param0.measure
     */
    onMeasureSelected({ measure }) {
        this.model.updateMetaData({ measure });
    }

    /**
     * Export cohort data in Excel file
     */
    async downloadExcel() {
        const {
            title,
            resModel,
            interval,
            measure,
            measures,
            dateStartString,
            dateStopString,
            timeline,
        } = this.model.metaData;
        const { domains } = this.model.searchParams;
        const data = {
            title: title,
            model: resModel,
            interval_string: this.model.intervals[interval].toString(), // intervals are lazy-translated
            measure_string: measures[measure].string,
            date_start_string: dateStartString,
            date_stop_string: dateStopString,
            timeline: timeline,
            rangeDescription: domains[0].description,
            report: this.model.data[0],
            comparisonRangeDescription: domains[1] && domains[1].description,
            comparisonReport: this.model.data[1],
        };
        this.env.services.ui.block();
        try {
            // FIXME: [SAD/JPP] some data seems to be missing from the export in master. (check the python)
            await download({
                url: "/web/cohort/export",
                data: { data: new Blob([JSON.stringify(data)], { type: "application/json" }) },
            });
        } finally {
            this.env.services.ui.unblock();
        }
    }
}
