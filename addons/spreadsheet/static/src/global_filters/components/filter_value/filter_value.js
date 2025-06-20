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
import { BooleanMultiSelector } from "../boolean_multi_selector/boolean_multi_selector";
import { SelectionFilterValue } from "../selection_filter_value/selection_filter_value";

const { ValidationMessages } = components;

export class FilterValue extends Component {
    static template = "spreadsheet.FilterValue";
    static components = {
        TextFilterValue,
        DateFilterValue,
        MultiRecordSelector,
        BooleanMultiSelector,
        SelectionFilterValue,
        ValidationMessages,
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
        this.nameService = useService("name");
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

    onDateInput(id, value) {
        this.props.setGlobalFilterValue(id, value);
    }

    onTextInput(id, value) {
        if (Array.isArray(value) && value.length === 0) {
            this.clear(id);
            return;
        }
        this.props.setGlobalFilterValue(id, value);
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
        this.props.setGlobalFilterValue(id, value);
    }

    async onTagSelected(id, resIds) {
        if (!resIds.length) {
            // force clear, even automatic default values
            this.clear(id);
        } else {
            const displayNames = await this.nameService.loadDisplayNames(
                this.filter.modelName,
                resIds
            );
            this.props.setGlobalFilterValue(id, resIds, Object.values(displayNames));
        }
    }

    clear(id) {
        this.props.setGlobalFilterValue(id);
    }
}
