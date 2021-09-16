odoo.define('web.GroupByMenu', function (require) {
    "use strict";

    const CustomGroupByItem = require('web.CustomGroupByItem');
    const { FACET_ICONS, GROUPABLE_TYPES } = require('web.searchUtils');
    const { useModel } = require('web.Model');

    const { Component } = owl;

    class GroupByMenu extends Component {

        constructor() {
            super(...arguments);
            this.icon = FACET_ICONS.groupBy;

            this.fields = Object.values(this.props.fields)
                .filter(field => this._validateField(field))
                .sort(({ string: a }, { string: b }) => a > b ? 1 : a < b ? -1 : 0);

            this.model = useModel('searchModel');
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @override
         */
        get items() {
            return this.model.get('filters', f => f.type === 'groupBy');
        }

        //---------------------------------------------------------------------
        // Private
        //---------------------------------------------------------------------

        /**
         * @see {@link odoo/fields.py} Field._description_sortable
         * @see {@link odoo/fields.py} Many2Many.groupable
         * @private
         * @param {Object} field
         * @returns {boolean}
         */
        _validateField(field) {
            return (field.sortable || (field.type === "many2many" && field.store)) &&
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
        onGroupBySelected(ev) {
            ev.stopPropagation();
            const { itemId, optionId } = ev.detail.payload;
            if (optionId) {
                this.model.dispatch('toggleFilterWithOptions', itemId, optionId);
            } else {
                this.model.dispatch('toggleFilter', itemId);
            }
        }
    }

    GroupByMenu.components = { CustomGroupByItem };
    GroupByMenu.props = { fields: Object };
    GroupByMenu.template = "web.GroupByMenu";

    return GroupByMenu;
});
