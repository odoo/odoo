odoo.define('web.FilterMenu', function (require) {
    "use strict";

    const CustomFilterItem = require('web.CustomFilterItem');
    const DropdownMenu = require('web.DropdownMenu');
    const { FACET_ICONS } = require("web.searchUtils");
    const { useModel } = require('web/static/src/js/model.js');

    /**
     * 'Filters' menu
     *
     * Simple rendering of the filters of type `filter` given by the control panel
     * model. It uses most of the behaviours implemented by the dropdown menu Component,
     * with the addition of a filter generator (@see CustomFilterItem).
     * @see DropdownMenu for additional details.
     * @extends DropdownMenu
     */
    class FilterMenu extends DropdownMenu {

        constructor() {
            super(...arguments);

            this.model = useModel('searchModel');
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @override
         */
        get icon() {
            return FACET_ICONS.filter;
        }

        /**
         * @override
         */
        get items() {
            return this.model.get('filters', f => f.type === 'filter');
        }

        /**
         * @override
         */
        get title() {
            return this.env._t("Filters");
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {OwlEvent} ev
         */
        _onItemSelected(ev) {
            ev.stopPropagation();
            const { item, option } = ev.detail;
            if (option) {
                this.model.dispatch('toggleFilterWithOptions', item.id, option.id);
            } else {
                this.model.dispatch('toggleFilter', item.id);
            }
        }
    }

    FilterMenu.components = Object.assign({}, DropdownMenu.components, {
        CustomFilterItem,
    });
    FilterMenu.props = Object.assign({}, DropdownMenu.props, {
        fields: Object,
    });
    FilterMenu.template = 'web.FilterMenu';

    return FilterMenu;
});
