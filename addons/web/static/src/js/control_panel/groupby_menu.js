odoo.define('web.GroupByMenu', function (require) {
    "use strict";

    const { GROUPABLE_TYPES } = require('web.searchUtils');
    const DropdownMenu = require('web.DropdownMenu');
    const CustomGroupByItem = require('web.CustomGroupByItem');
    const { useModel } = require('web.model');

    /**
     * 'Group by' menu
     *
     * Simple rendering of the filters of type `groupBy` given by the control panel
     * model. It uses most of the behaviours implemented by the dropdown menu Component,
     * with the addition of a groupBy filter generator (@see CustomGroupByItem).
     * @see DropdownMenu for additional details.
     * @extends DropdownMenu
     */
    class GroupByMenu extends DropdownMenu {

        constructor() {
            super(...arguments);

            this.fields = Object.values(this.props.fields)
                .filter(field => this._validateField(field))
                .sort(({ string: a }, { string: b }) => a > b ? 1 : a < b ? -1 : 0);

            this.model = useModel('controlPanelModel');
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @override
         */
        get items() {
            return this.model.getFiltersOfType('groupBy');
        }

        /**
         * @override
         */
        get title() {
            return this.env._t("Group By");
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {Object} field
         * @returns {boolean}
         */
        _validateField(field) {
            return field.sortable &&
                field.name !== "id" &&
                GROUPABLE_TYPES.includes(field.type);
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

    GroupByMenu.components = Object.assign({}, DropdownMenu.components, {
        CustomGroupByItem,
    });
    GroupByMenu.defaultProps = Object.assign({}, DropdownMenu.defaultProps, {
        icon: 'fa fa-bars',
    });
    GroupByMenu.props = Object.assign({}, DropdownMenu.props, {
        fields: Object,
    });
    GroupByMenu.template = 'web.GroupByMenu';

    return GroupByMenu;
});
