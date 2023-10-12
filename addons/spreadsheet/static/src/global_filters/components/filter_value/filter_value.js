/** @odoo-module */

import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";
import { DateFilterValue } from "../filter_date_value/filter_date_value";
import { DateFromToValue } from "../filter_date_from_to_value/filter_date_from_to_value";

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class FilterValue extends Component {
    setup() {
        this.getters = this.props.model.getters;
        this.relativeDateRangesTypes = RELATIVE_DATE_RANGE_TYPES;
        this.nameService = useService("name");
    }
    onDateInput(id, value) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", { id, value });
    }

    onTextInput(id, value) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", { id, value });
    }

    async onTagSelected(id, resIds) {
        if (!resIds.length) {
            // force clear, even automatic default values
            this.clear(id);
        } else {
            const displayNames = await this.nameService.loadDisplayNames(
                this.props.filter.modelName,
                resIds
            );
            this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
                id,
                value: resIds,
                displayNames: Object.values(displayNames),
            });
        }
    }

    translate(text) {
        return _t(text);
    }

    clear(id) {
        this.props.model.dispatch("CLEAR_GLOBAL_FILTER_VALUE", { id });
    }
}
FilterValue.template = "spreadsheet_edition.FilterValue";
FilterValue.components = { DateFilterValue, DateFromToValue, MultiRecordSelector };
FilterValue.props = {
    filter: Object,
    model: Object,
};
