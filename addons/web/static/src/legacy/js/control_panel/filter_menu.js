odoo.define('web.FilterMenu', function (require) {
    "use strict";

    const { Dropdown } = require("@web/core/dropdown/dropdown");
    const { SearchDropdownItem } = require("@web/search/search_dropdown_item/search_dropdown_item");
    const CustomFilterItem = require('web.CustomFilterItem');
    const { FACET_ICONS } = require("web.searchUtils");
    const { useModel } = require('web.Model');
    const { LegacyComponent } = require("@web/legacy/legacy_component");

    /**
     * 'Filters' menu
     *
     * Simple rendering of the filters of type `filter` given by the control panel
     * model. It uses most of the behaviours implemented by the dropdown menu Component,
     * with the addition of a filter generator (@see CustomFilterItem).
     */
    class FilterMenu extends LegacyComponent {

        setup() {
            this.icon = FACET_ICONS.filter;
            this.model = useModel('searchModel');
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @override
         */
        get items() {
            return this.model.get('filters', f => f.type === 'filter');
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {Object} param0
         * @param {number} param0.itemId
         * @param {number} [param0.optionId]
         */
        onFilterSelected({ itemId, optionId }) {
            if (optionId) {
                this.model.dispatch('toggleFilterWithOptions', itemId, optionId);
            } else {
                this.model.dispatch('toggleFilter', itemId);
            }
        }
    }

    FilterMenu.defaultProps = {
        class: "",
    };
    FilterMenu.props = {
        fields: Object,
        class: { String, optional: true },
    };
    FilterMenu.template = "web.legacy.FilterMenu";
    FilterMenu.components = { CustomFilterItem, Dropdown, DropdownItem: SearchDropdownItem };

    return FilterMenu;
});
