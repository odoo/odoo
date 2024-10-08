import { Component, useExternalListener, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useAutofocus, useService } from "@web/core/utils/hooks";

export class SearchBar extends Component {
    static template = "point_of_sale.SearchBar";
    static props = {
        model: String,
        fields: Object,
        searches: Object,
        filters: { type: Object, optional: true },
        defaults: { type: Object, optional: true },
        placeholder: String,
        callback: Function,
    };

    setup() {
        this.ui = useState(useService("ui"));
        this.pos = usePos();
        this.searchByOptions = this.props.fields.search;
        this.filterByOptions = Object.values(this.props.filters || {});

        if (this.filterByOptions.length) {
            this.selectionNameByVal = this.filterOptions
                .flatMap((opt) => opt.selection)
                .reduce((acc, val) => {
                    acc[val[0]] = val[1];
                    return acc;
                }, {});
        }

        useAutofocus();
        useExternalListener(window, "click", this.hideOptions);

        this.state = useState({
            showSearchFields: false,
            showFilterOptions: false,
            selectedSearch: false,
            selectedSearchValue: "",
            selectedFilter: this.props.defaults?.filter?.name,
            selectedFilterValue: this.props.defaults?.filter?.value,
        });

        if (this.props.defaults?.filter?.name && this.props.defaults?.filter?.value) {
            this.actionCallback();
        }
    }

    get viewSearch() {
        return this.pos.data.viewSearch[this.props.model].models;
    }

    get filterOptions() {
        const availableSelection = [];

        for (const params of this.filterByOptions) {
            availableSelection.push({
                field: params.field,
                name: params.string,
                selection: params.values,
            });
        }

        return availableSelection;
    }

    getFieldName(field) {
        return this.pos.data.relations[this.props.model][field].string;
    }

    actionCallback() {
        const payload = {
            searchField: this.state.selectedSearch,
            searchValue: this.state.selectedSearchValue,
            filterField: this.state.selectedFilter,
            filterValue: this.state.selectedFilterValue,
        };

        this.props.callback(payload);
    }

    onSelectFilter(field, key) {
        this.state.selectedFilter = field;
        this.state.selectedFilterValue = key;
        this.actionCallback();
    }

    onClickSearchField(fieldName) {
        this.state.selectedSearch = fieldName;
        this.state.showSearchFields = false;
        this.actionCallback();
    }

    onSearchInputKeydown(event) {
        if (["ArrowUp", "ArrowDown"].includes(event.key)) {
            event.preventDefault();
        }
    }

    onSearchInputKeyup(event) {
        if (["ArrowUp", "ArrowDown"].includes(event.key)) {
            const newFields = this.fieldIdToSelect(event.key);
            this.state.selectedSearch = newFields;
            this.state.showSearchFields = this.filterByOptions.length ? true : false;
        } else if (event.key === "Enter" || this.state.selectedSearchValue == "") {
            this.state.showSearchFields = false;
            this.actionCallback();
        } else {
            if (this.state.showSearchFields === -1 && this.searchFieldsList.length) {
                this.state.showSearchFields = 0;
            }
            this.state.showSearchFields = this.filterByOptions.length ? true : false;
        }
    }

    fieldIdToSelect(key) {
        const length = this.searchByOptions.length;

        if (!length) {
            return null;
        }

        const currentIndex = this.searchByOptions.indexOf(this.state.selectedSearch);
        const newIndex = (currentIndex + (key === "ArrowDown" ? 1 : -1)) % length;
        return this.searchByOptions[newIndex];
    }

    hideOptions() {
        this.state.showFilterOptions = false;
        this.state.showSearchFields = false;
    }
}
