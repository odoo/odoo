/** @odoo-module */

import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";
import { DateFilterValue } from "../filter_date_value/filter_date_value";
<<<<<<< 17.0
import { DateFromToValue } from "../filter_date_from_to_value/filter_date_from_to_value";
||||||| c9c510eb2d4373ad0f65215609f87a0d1d4d80cf
=======
import { useService } from "@web/core/utils/hooks";
>>>>>>> f7a93a9d51fe639f3ba6e35f43a11ed0f9f69536

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { TextFilterValue } from "../filter_text_value/filter_text_value";

export class FilterValue extends Component {
    setup() {
        this.getters = this.props.model.getters;
        this.relativeDateRangesTypes = RELATIVE_DATE_RANGE_TYPES;
<<<<<<< 17.0
        this.nameService = useService("name");
||||||| c9c510eb2d4373ad0f65215609f87a0d1d4d80cf
=======
        this.orm = useService("orm");
>>>>>>> f7a93a9d51fe639f3ba6e35f43a11ed0f9f69536
    }

    get filter() {
        return this.props.filter;
    }

    get filterValue() {
        return this.getters.getGlobalFilterValue(this.filter.id);
    }

    get textAllowedValues() {
        return this.getters.getTextFilterOptions(this.filter.id);
    }

    onDateInput(id, value) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", { id, value });
    }

    onTextInput(id, value) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", { id, value });
    }

<<<<<<< 17.0
    async onTagSelected(id, resIds) {
        if (!resIds.length) {
            // force clear, even automatic default values
            this.clear(id);
        } else {
            const displayNames = await this.nameService.loadDisplayNames(
                this.filter.modelName,
                resIds
            );
            this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
                id,
                value: resIds,
                displayNames: Object.values(displayNames),
            });
        }
||||||| c9c510eb2d4373ad0f65215609f87a0d1d4d80cf
    onTagSelected(id, values) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
            id,
            value: values.map((record) => record.id),
            displayNames: values.map((record) => record.display_name),
        });
=======
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
>>>>>>> f7a93a9d51fe639f3ba6e35f43a11ed0f9f69536
    }

    translate(text) {
        return _t(text);
    }

    clear(id) {
        this.props.model.dispatch("CLEAR_GLOBAL_FILTER_VALUE", { id });
    }
}
FilterValue.template = "spreadsheet_edition.FilterValue";
FilterValue.components = { DateFilterValue, DateFromToValue, MultiRecordSelector, TextFilterValue };
FilterValue.props = {
    filter: Object,
    model: Object,
};
