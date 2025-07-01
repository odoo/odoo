import { Component, useState } from "@odoo/owl";
import { FilterValue } from "@spreadsheet/global_filters/components/filter_value/filter_value";
import { Dialog } from "@web/core/dialog/dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

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
        this.state = useState({
            activeFilters: this.globalFilters
                .filter((globalFilter) =>
                    this.props.model.getters.isGlobalFilterActive(globalFilter.id)
                )
                .map((globalFilter) => ({
                    globalFilter,
                    value: this.props.model.getters.getGlobalFilterValue(globalFilter.id),
                })),
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
        this.state.activeFilters.push({ globalFilter: filter });
    }

    getFilterLabel(node) {
        return _t(node.globalFilter.label); // Label is extracted from the spreadsheet json file
    }

    setGlobalFilterValue(node, value) {
        node.value = value;
    }

    getTranslatedFilterLabel(filter) {
        return _t(filter.label); // Label is extracted from the spreadsheet json file
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
            if (node) {
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
}
