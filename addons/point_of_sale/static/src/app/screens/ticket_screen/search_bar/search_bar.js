/** @odoo-module */

import { Component, useExternalListener, useState } from "@odoo/owl";
import { useAutofocus, useService } from "@web/core/utils/hooks";

/**
 * This is a simple configurable search bar component. It has search fields
 * and selection filter. Search fields allow the users to specify the type
 * of their searches. The filter is a dropdown menu for selection. Depending on
 * user's action, this component emits corresponding event with the action
 * information (payload).
 *
 * TODO: This component can be made more generic and be able to replace
 * all the search bars across pos ui.
 *
 * @prop {{
 *  config: {
 *      searchFields: Map<string, string>,
 *      filter: { show: boolean, options: Map<string, { text: string, indented: boolean? }> }
 *  },
 *  placeholder: string,
 * }}
 * @emits search @payload { fieldName: string, searchTerm: '' }
 *
 * NOTE: The payload of the emitted event is accessible via the `detail`
 * field of the event.
 */
export class SearchBar extends Component {
    static template = "point_of_sale.SearchBar";

    setup() {
        this.ui = useState(useService("ui"));
        useAutofocus();
        useExternalListener(window, "click", this._hideOptions);
        this.filterOptionsList = [...this.props.config.filter.options.keys()];
        this.searchFieldsList = [...this.props.config.searchFields.keys()];
        const defaultSearchFieldId = this.searchFieldsList.indexOf(
            this.props.config.defaultSearchDetails.fieldName
        );
        this.state = useState({
            searchInput: this.props.config.defaultSearchDetails.searchTerm || "",
            selectedSearchFieldId: defaultSearchFieldId == -1 ? 0 : defaultSearchFieldId,
            showSearchFields: false,
            showFilterOptions: false,
            selectedFilter: this.props.config.defaultFilter || this.filterOptionsList[0],
        });
    }
    _onSelectFilter(key) {
        this.state.selectedFilter = key;
        this.props.onFilterSelected(this.state.selectedFilter);
    }
    /**
     * When pressing vertical arrow keys, do not move the input cursor.
     */
    onSearchInputKeydown(event) {
        if (["ArrowUp", "ArrowDown"].includes(event.key)) {
            event.preventDefault();
        }
    }
    /**
     * When vertical arrow keys are pressed, select fields for searching.
     * When enter key is pressed, trigger search event if there is searchInput.
     */
    onSearchInputKeyup(event) {
        if (["ArrowUp", "ArrowDown"].includes(event.key)) {
            this.state.selectedSearchFieldId = this._fieldIdToSelect(event.key);
        } else if (event.key === "Enter" || this.state.searchInput == "") {
            this._onClickSearchField(this.searchFieldsList[this.state.selectedSearchFieldId]);
        } else {
            if (this.state.selectedSearchFieldId === -1 && this.searchFieldsList.length) {
                this.state.selectedSearchFieldId = 0;
            }
            this.state.showSearchFields = true;
        }
    }
    /**
     * Called when a search field is clicked.
     */
    _onClickSearchField(fieldName) {
        this.state.showSearchFields = false;
        this.props.onSearch({ fieldName, searchTerm: this.state.searchInput });
    }
    /**
     * Given an arrow key, return the next selectedSearchFieldId.
     * E.g. If the selectedSearchFieldId is 1 and ArrowDown is pressed, return 2.
     *
     * @param {string} key vertical arrow key
     */
    _fieldIdToSelect(key) {
        const length = this.searchFieldsList.length;
        if (!length) {
            return null;
        }
        if (this.state.selectedSearchFieldId === -1) {
            return 0;
        }
        const current = this.state.selectedSearchFieldId || length;
        return (current + (key === "ArrowDown" ? 1 : -1)) % length;
    }
    _hideOptions() {
        this.state.showFilterOptions = false;
        this.state.showSearchFields = false;
    }
}
