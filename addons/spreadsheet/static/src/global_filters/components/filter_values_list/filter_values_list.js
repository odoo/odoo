import { Component, onWillStart, useState } from "@odoo/owl";
import { FilterValue } from "@spreadsheet/global_filters/components/filter_value/filter_value";
import { _t } from "@web/core/l10n/translation";
import { getOperatorLabel } from "@web/core/tree_editor/tree_editor_operator_editor";
import {
    getDefaultValue,
    getEmptyFilterValue,
    getFilterTypeOperators,
} from "@spreadsheet/global_filters/helpers";
import { useService } from "@web/core/utils/hooks";
import { isEmptyFilterValue } from "../../helpers";
import { deepEqual } from "@web/core/utils/objects";

/**
 * This component is used to display a list of all the global filters of a
 * spreadsheet/dashboard. It allows the user to select the values of the filters
 * and confirm or discard the changes.
 */
export class FilterValuesList extends Component {
    static template = "spreadsheet_dashboard.FilterValuesList";
    static components = { FilterValue };

    static props = {
        close: Function,
        model: Object,
        openFiltersEditor: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            filtersAndValues: this.globalFilters.map((globalFilter) => {
                const value = this.props.model.getters.getGlobalFilterValue(globalFilter.id);
                return {
                    globalFilter,
                    value: value ? { ...value } : getDefaultValue(globalFilter.type),
                };
            }),
        });
        onWillStart(async () => {
            this.searchableParentRelations = await this.fetchSearchableParentRelation();
        });
    }

    get globalFilters() {
        return this.props.model.getters.getGlobalFilters();
    }

    setGlobalFilterValue(node, value) {
        if (value == undefined && node.globalFilter.type !== "date") {
            // preserve the operator.
            node.value = {
                ...node.value,
                ...getEmptyFilterValue(node.globalFilter, node.value.operator),
            };
        } else {
            node.value = value;
        }
    }

    getTranslatedFilterLabel(filter) {
        return _t(filter.label); // Label is extracted from the spreadsheet json file
    }

    getOperators(filter) {
        const operators = getFilterTypeOperators(filter.type);
        if (filter.type === "relation" && !this.searchableParentRelations[filter.modelName]) {
            return operators.filter((op) => op !== "child_of");
        }
        return filter.type === "boolean" ? [undefined, ...operators] : operators;
    }

    filterHasClearButton(node) {
        return !isEmptyFilterValue(node.globalFilter, node.value);
    }

    getOperatorLabel(operator) {
        return operator ? getOperatorLabel(operator) : "";
    }

    updateOperator(node, operator) {
        if (!operator) {
            node.value = undefined;
            return;
        }
        if (!node.value) {
            node.value = {};
        }
        node.value.operator = operator;
        const defaultValue = getEmptyFilterValue(node.globalFilter, operator);
        for (const key of Object.keys(defaultValue ?? {})) {
            if (!(key in node.value)) {
                node.value[key] = defaultValue[key];
            }
        }
    }

    clearFilter(filterId) {
        const node = this.state.filtersAndValues.find((node) => node.globalFilter.id === filterId);
        if (node && node.value) {
            const emptyValue = getEmptyFilterValue(node.globalFilter, node.value.operator);
            node.value =
                typeof emptyValue === "object"
                    ? { ...emptyValue, operator: node.value.operator }
                    : emptyValue;
        }
    }

    onConfirm() {
        for (const node of this.state.filtersAndValues) {
            const { globalFilter, value } = node;
            const originalValue = this.props.model.getters.getGlobalFilterValue(globalFilter.id);

            if (deepEqual(originalValue, value)) {
                continue;
            }
            this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
                id: globalFilter.id,
                value: isEmptyFilterValue(globalFilter, value) ? undefined : value,
            });
        }
        this.props.close();
    }

    onDiscard() {
        this.props.close();
    }

    fetchSearchableParentRelation() {
        const models = this.globalFilters
            .filter((filter) => filter.type === "relation")
            .map((filter) => filter.modelName);
        return this.orm
            .cache({ type: "disk" })
            .call("ir.model", "has_searchable_parent_relation", [models]);
    }
}
