/** @odoo-module alias=web.GroupByMenu **/
    
    import { Dropdown } from "@web/core/dropdown/dropdown";
    import { SearchDropdownItem } from "@web/search/search_dropdown_item/search_dropdown_item";
    import { CustomGroupByItem } from "@web/search/custom_group_by_item/custom_group_by_item";
    import { FACET_ICONS, GROUPABLE_TYPES } from "web.searchUtils";
    import { useModel } from "web.Model";
    import { LegacyComponent } from "@web/legacy/legacy_component";

    class GroupByMenu extends LegacyComponent {

        setup() {
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
            return (field.type === "many2many" ? field.store : field.sortable) &&
                field.name !== "id" &&
                GROUPABLE_TYPES.includes(field.type);
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @param {Object} param0
         * @param {number} param0.itemId
         * @param {number} [param0.optionId]
         */
        onGroupBySelected({ itemId, optionId }) {
            if (optionId) {
                this.model.dispatch('toggleFilterWithOptions', itemId, optionId);
            } else {
                this.model.dispatch('toggleFilter', itemId);
            }
        }
        onAddCustomGroup(fieldName) {
            const field = this.props.fields[fieldName];
            this.model.dispatch("createNewGroupBy", field);
        }
    }

    GroupByMenu.components = { CustomGroupByItem, Dropdown, SearchDropdownItem };
    GroupByMenu.props = { fields: Object };
    GroupByMenu.template = "web.legacy.GroupByMenu";

    export default GroupByMenu;
