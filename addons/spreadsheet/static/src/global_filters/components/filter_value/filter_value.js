/** @ts-check */

import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { DateFilterValue } from "../date_filter_value/date_filter_value";

import { Component, onWillStart } from "@odoo/owl";
import { components } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { user } from "@web/core/user";
import { TextFilterValue } from "../filter_text_value/filter_text_value";
import { getFields, ModelNotFoundError } from "@spreadsheet/data_sources/data_source";
import { SelectionFilterValue } from "../selection_filter_value/selection_filter_value";
import {
    isTextualOperator,
    isSetOperator,
    getDefaultValue,
} from "@spreadsheet/global_filters/helpers";
import { NumericFilterValue } from "../numeric_filter_value/numeric_filter_value";

const { ValidationMessages } = components;

export class FilterValue extends Component {
    static template = "spreadsheet.FilterValue";
    static components = {
        TextFilterValue,
        DateFilterValue,
        MultiRecordSelector,
        SelectionFilterValue,
        ValidationMessages,
        NumericFilterValue,
    };
    static props = {
        filter: Object,
        model: Object,
        setGlobalFilterValue: Function,
        globalFilterValue: { optional: true },
        showTitle: { type: Boolean, optional: true },
        showClear: { type: Boolean, optional: true },
    };

    setup() {
        this.getters = this.props.model.getters;
        this.fieldService = useService("field");
        this.isValid = false;
        onWillStart(async () => {
            if (this.filter.type !== "relation") {
                this.isValid = true;
                return;
            }
            try {
                await getFields(this.fieldService, this.filter.modelName);
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

    get isTextualOperator() {
        return isTextualOperator(this.filterValue?.operator);
    }

    get isSetOperator() {
        return isSetOperator(this.filterValue?.operator);
    }

    get filter() {
        return this.props.filter;
    }

    get filterValue() {
        return this.props.globalFilterValue;
    }

    get textAllowedValues() {
        return this.getters.getTextFilterOptions(this.filter.id);
    }

    get relationalAllowedDomain() {
        const domain = this.props.filter.domainOfAllowedValues;
        if (domain) {
            return new Domain(domain).toList(user.context);
        }
        return [];
    }

    get invalidModel() {
        const model = this.filter.modelName;
        return _t(
            "The model (%(model)s) of this global filter is not valid (it may have been renamed/deleted).",
            {
                model,
            }
        );
    }

    getDefaultOperator() {
        return getDefaultValue(this.filter.type).operator;
    }

    onDateInput(id, value) {
        this.props.setGlobalFilterValue(id, value);
    }

    onTextInput(id, value) {
        if (Array.isArray(value) && value.length === 0) {
            this.clear(id);
            return;
        }
        const operator = this.filterValue?.operator ?? this.getDefaultOperator();
        this.props.setGlobalFilterValue(id, { operator, strings: value });
    }

    onTargetValueNumericInput(id, value) {
        const operator = this.filterValue?.operator ?? this.getDefaultOperator();
        const newFilterValue = {
            operator,
            targetValue: value,
        };
        this.props.setGlobalFilterValue(id, newFilterValue);
    }

    reorderValues(min, max) {
        if (min > max) {
            const tmp = min;
            min = max;
            max = tmp;
        }
        return { minimumValue: min, maximumValue: max };
    }

    onMinimumValueNumericInput(id, value) {
        const operator = this.filterValue?.operator ?? this.getDefaultOperator();
        const newFilterValue = {
            operator,
            ...this.reorderValues(value, this.filterValue?.maximumValue),
        };
        this.props.setGlobalFilterValue(id, newFilterValue);
    }

    onMaximumValueNumericInput(id, value) {
        const operator = this.filterValue?.operator ?? this.getDefaultOperator();
        const newFilterValue = {
            operator,
            ...this.reorderValues(this.filterValue?.minimumValue, value),
        };
        this.props.setGlobalFilterValue(id, newFilterValue);
    }

    onBooleanInput(id, value) {
        if (Array.isArray(value) && value.length === 0) {
            this.clear(id);
            return;
        }
        this.props.setGlobalFilterValue(id, value);
    }

    onSelectionInput(id, value) {
        if (Array.isArray(value) && value.length === 0) {
            this.clear(id);
            return;
        }
        const operator = this.filterValue?.operator ?? this.getDefaultOperator();
        this.props.setGlobalFilterValue(id, { operator, selectionValues: value });
    }

    async onTagSelected(id, resIds) {
        if (!resIds.length) {
            // force clear, even automatic default values
            this.clear(id);
        } else {
            const operator = this.filterValue?.operator ?? this.getDefaultOperator();
            this.props.setGlobalFilterValue(id, { operator, ids: resIds });
        }
    }

    clear(id) {
        this.props.setGlobalFilterValue(id);
    }
}
