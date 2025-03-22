/** @odoo-module */

import { RecordsSelector } from "../records_selector/records_selector";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";
import { DateFilterValue } from "../filter_date_value/filter_date_value";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

export class FilterValue extends Component {
    setup() {
        this.getters = this.props.model.getters;
        this.relativeDateRangesTypes = RELATIVE_DATE_RANGE_TYPES;
        this.orm = useService("orm");
    }
    onDateInput(id, value) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", { id, value });
    }

    onTextInput(id, value) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", { id, value });
    }

    async onTagSelected(id, values) {
        let records = values;
        if (values.some((record) => record.display_name === undefined)) {
            ({ records } = await this.orm.webSearchRead(
                this.props.filter.modelName,
                [["id", "in", values.map((record) => record.id)]],
                ["display_name"]
            ));
        }
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
            id,
            value: records.map((record) => record.id),
            displayNames: records.map((record) => record.display_name),
        });
    }

    onClear(id) {
        this.props.model.dispatch("CLEAR_GLOBAL_FILTER_VALUE", { id });
    }
}
FilterValue.template = "spreadsheet_edition.FilterValue";
FilterValue.components = { RecordsSelector, DateFilterValue };
FilterValue.props = {
    filter: Object,
    model: Object,
    showTitle: { type: Boolean, optional: true },
};
