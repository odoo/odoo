/** @ts-check */

import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";
import { DateFilterValue } from "../filter_date_value/filter_date_value";
import { DateFromToValue } from "../filter_date_from_to_value/filter_date_from_to_value";

import { Component, onWillStart } from "@odoo/owl";
import { components } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { user } from "@web/core/user";
import { TextFilterValue } from "../filter_text_value/filter_text_value";
import { getFields, ModelNotFoundError } from "@spreadsheet/data_sources/data_source";
import { isDateOperator } from "@spreadsheet/global_filters/helpers";

const { ValidationMessages } = components;

export class FilterValue extends Component {
    static template = "spreadsheet_edition.FilterValue";
    static components = {
        DateFilterValue,
        DateFromToValue,
        MultiRecordSelector,
        TextFilterValue,
        ValidationMessages,
    };
    static props = {
        filter: Object,
        model: Object,
    };

    setup() {
        this.fieldService = useService("field");
        this.relativeDateRangesTypes = RELATIVE_DATE_RANGE_TYPES;
        this.isValid = false;
        onWillStart(async () => {
            if (!this.filter.relation) {
                this.isValid = true;
                return;
            }
            try {
                await getFields(this.fieldService, this.filter.relation);
                this.isValid = true;
            } catch (e) {
                if (e instanceof ModelNotFoundError) {
                    this.isValid = false;
                } else {
                    throw e;
                }
            }
        });
    }

    get filter() {
        return this.props.filter;
    }

    get filterValue() {
        return this.props.model.getters.getGlobalFilterValue(this.filter.id);
    }

    get textAllowedValues() {
        return this.props.model.getters.getTextFilterOptions(this.filter.id);
    }

    get relationalAllowedDomain() {
        const domain = this.props.filter.domainOfAllowedValues;
        if (domain) {
            return new Domain(domain).toList(user.context);
        }
        return [];
    }

    get invalidModel() {
        const model = this.filter.relation;
        return _t(
            "The model (%(model)s) of this global filter is not valid (it may have been renamed/deleted).",
            {
                model,
            }
        );
    }

    get isDateFilter() {
        return isDateOperator(this.filter.operator);
    }

    setFilterValue(value) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
            id: this.filter.id,
            value,
        });
    }

    translate(text) {
        return _t(text);
    }
}
