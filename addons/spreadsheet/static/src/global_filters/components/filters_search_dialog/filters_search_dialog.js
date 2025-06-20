import { Component, onWillStart, useState } from "@odoo/owl";
import { FilterValue } from "@spreadsheet/global_filters/components/filter_value/filter_value";
import { Dialog } from "@web/core/dialog/dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { getOperatorLabel } from "@web/core/tree_editor/tree_editor_operator_editor";
import {
    getDefaultValue,
    getEmptyFilterValue,
    getFilterTypeOperators,
} from "@spreadsheet/global_filters/helpers";
import { useService } from "@web/core/utils/hooks";
import { isEmptyFilterValue } from "../../helpers";

/**
 * This component is used to display a dialog with the global filters of a
 * spreadsheet/dashboard. It allows the user to select the values of the filters
 * and confirm or discard the changes.
 */
export class FiltersSearchDialog extends Component {
    static template = "spreadsheet_dashboard.FiltersSearchDialog";
    static components = {
        Dialog,
        Dropdown,
        DropdownItem,
        FilterValue,
    };

    static props = {
        close: Function,
        model: Object,
        openFiltersEditor: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            activeFilters: this.globalFilters
                .filter((globalFilter) =>
                    this.props.model.getters.isGlobalFilterActive(globalFilter.id)
                )
                .map((globalFilter) => ({
                    globalFilter,
                    value: { ...this.props.model.getters.getGlobalFilterValue(globalFilter.id) },
                })),
        });
        onWillStart(async () => {
            this.searchableParentRelations = await this.fetchSearchableParentRelation();
        });
    }

    get globalFilters() {
        return this.props.model.getters.getGlobalFilters();
    }

    get hasUnusedGlobalFilters() {
        return this.globalFilters.length > this.state.activeFilters.length;
    }

    get unusedGlobalFilters() {
        return this.globalFilters.filter(
            (globalFilter) =>
                !this.state.activeFilters.some((node) => node.globalFilter.id === globalFilter.id)
        );
    }

    activateFilter(filter) {
        this.state.activeFilters.push({
            globalFilter: filter,
            value: getDefaultValue(filter.type),
        });
    }

    getFilterLabel(node) {
        return _t(node.globalFilter.label); // Label is extracted from the spreadsheet json file
    }

    setGlobalFilterValue(node, value) {
        if (!value && node.globalFilter.type !== "date") {
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
        return operators;
    }

    getOperatorLabel(operator) {
        return getOperatorLabel(operator);
    }

    updateOperator(node, operator) {
        node.value.operator = operator;
        const defaultValue = getEmptyFilterValue(node.globalFilter, operator);
        for (const key of Object.keys(defaultValue ?? {})) {
            if (!(key in node.value)) {
                node.value[key] = defaultValue[key];
            }
        }
    }

    removeFilter(filterId) {
        const index = this.state.activeFilters.findIndex(
            (node) => node.globalFilter.id === filterId
        );
        if (index !== -1) {
            this.state.activeFilters.splice(index, 1);
        }
    }

    onConfirm() {
        for (const filter of this.globalFilters) {
            const node = this.state.activeFilters.find(
                (node) => node.globalFilter.id === filter.id
            );
            if (node && !isEmptyFilterValue(filter, node.value)) {
                this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
                    id: filter.id,
                    value: node.value,
                });
            } else {
                this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", { id: filter.id });
            }
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
        return this.orm.cached().call("ir.model", "has_searchable_parent_relation", [models]);
    }
}
