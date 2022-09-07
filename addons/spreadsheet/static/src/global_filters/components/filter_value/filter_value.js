/** @odoo-module */

import { X2ManyTagSelector } from "../tag_selector_widget";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";
import { DateFilterValue } from "../filter_date_value/filter_date_value";

const { Component } = owl;

export class FilterValue extends Component {
    setup() {
        this.getters = this.props.model.getters;
        this.relativeDateRangesTypes = RELATIVE_DATE_RANGE_TYPES;
    }
    onDateInput(id, value) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", { id, value });
    }

    onTextInput(id, value) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", { id, value });
    }

    onTagSelected(id, values) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
            id,
            value: values.map((record) => record.id),
            displayNames: values.map((record) => record.display_name),
        });
    }

    onClear(id) {
        this.props.model.dispatch("CLEAR_GLOBAL_FILTER_VALUE", { id });
    }
}
FilterValue.template = "spreadsheet_edition.FilterValue";
FilterValue.components = { X2ManyTagSelector, DateFilterValue };
FilterValue.props = {
    filter: Object,
    model: Object,
};
