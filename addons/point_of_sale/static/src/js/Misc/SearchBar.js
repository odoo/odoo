odoo.define('point_of_sale.SearchBar', function (require) {
    'use strict';

    const { useState, useExternalListener } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

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
     *      searchFields: string[],
     *      filter: { show: boolean, options: string[] }
     *  },
     *  placeholder: string,
     * }}
     * @emits search @payload { fieldValue: string, searchTerm: '' }
     * @emits filter-selected @payload { filter: string }
     *
     * NOTE: The payload of the emitted event is accessible via the `detail`
     * field of the event.
     */
    class SearchBar extends PosComponent {
        constructor() {
            super(...arguments);
            this.config = this.props.config;
            this.state = useState({
                searchInput: '',
                selectedFieldId: this.config.searchFields.length ? 0 : null,
                showSearchFields: false,
                showFilterOptions: false,
                selectedFilter: this.config.filter.options[0] || this.env._t('Select'),
            });
            useExternalListener(window, 'click', this._hideOptions);
        }
        selectFilter(option) {
            this.state.selectedFilter = option;
            this.trigger('filter-selected', { filter: this.state.selectedFilter });
        }
        get placeholder() {
            return this.props.placeholder;
        }
        /**
         * When vertical arrow keys are pressed, select fields for searching.
         * When enter key is pressed, trigger search event if there is searchInput.
         */
        onKeydown(event) {
            if (['ArrowUp', 'ArrowDown'].includes(event.key)) {
                event.preventDefault();
                this.state.selectedFieldId = this._fieldIdToSelect(event.key);
            } else if (event.key === 'Enter') {
                this.trigger('search', {
                    fieldValue: this.config.searchFields[this.state.selectedFieldId],
                    searchTerm: this.state.searchInput,
                });
                this.state.showSearchFields = false;
            } else {
                if (this.state.selectedFieldId === null && this.config.searchFields.length) {
                    this.state.selectedFieldId = 0;
                }
                this.state.showSearchFields = true;
            }
        }
        /**
         * Called when a search field is clicked.
         */
        onClickSearchField(id) {
            this.state.showSearchFields = false;
            this.trigger('search', {
                fieldValue: this.config.searchFields[id],
                searchTerm: this.state.searchInput,
            });
        }
        /**
         * Given an arrow key, return the next selectedFieldId.
         * E.g. If the selectedFieldId is 1 and ArrowDown is pressed, return 2.
         *
         * @param {string} key vertical arrow key
         */
        _fieldIdToSelect(key) {
            const length = this.config.searchFields.length;
            if (!length) return null;
            if (this.state.selectedFieldId === null) return 0;
            const current = this.state.selectedFieldId || length;
            return (current + (key === 'ArrowDown' ? 1 : -1)) % length;
        }
        _hideOptions() {
            this.state.showFilterOptions = false;
            this.state.showSearchFields = false;
        }
    }
    SearchBar.template = 'point_of_sale.SearchBar';
    SearchBar.defaultProps = {
        config: {
            searchFields: [],
            filter: {
                show: false,
                options: [],
            },
        },
        placeholder: 'Search ...',
    };

    Registries.Component.add(SearchBar);

    return SearchBar;
});
