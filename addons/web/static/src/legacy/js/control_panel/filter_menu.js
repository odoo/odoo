odoo.define('web.FilterMenu', function (require) {
    "use strict";

    const CustomFilterItem = require('web.CustomFilterItem');
    const { FACET_ICONS } = require("web.searchUtils");
    const { useModel } = require('web.Model');

    const { Component } = owl;

    /**
     * 'Filters' menu
     *
     * Simple rendering of the filters of type `filter` given by the control panel
     * model. It uses most of the behaviours implemented by the dropdown menu Component,
     * with the addition of a filter generator (@see CustomFilterItem).
     */
    class FilterMenu extends Component {

        constructor() {
            super(...arguments);
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
         * @param {OwlEvent} ev
         */
        onFilterSelected(ev) {
            ev.stopPropagation();
            const { itemId, optionId } = ev.detail.payload;
            if (optionId) {
                this.model.dispatch('toggleFilterWithOptions', itemId, optionId);
            } else {
                this.model.dispatch('toggleFilter', itemId);
            }
        }
    }

    FilterMenu.components = { CustomFilterItem };
    FilterMenu.props = { fields: Object };
    FilterMenu.template = "web.legacy.FilterMenu";

    return FilterMenu;
});
