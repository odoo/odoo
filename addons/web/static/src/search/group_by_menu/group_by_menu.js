/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { CustomGroupByItem } from "./custom_group_by_item";
import { FACET_ICONS, GROUPABLE_TYPES } from "../utils/misc";
import { sortBy } from "@web/core/utils/arrays";
import { useBus } from "@web/core/utils/hooks";

const { Component } = owl;

export class GroupByMenu extends Component {
    setup() {
        this.icon = FACET_ICONS.groupBy;
        this.dropdownProps = Object.keys(this.props)
            .filter((key) => key in Dropdown.props)
            .reduce((obj, key) => ({ ...obj, [key]: this.props[key] }), {});
        const fields = [];
        for (const [fieldName, field] of Object.entries(this.env.searchModel.searchViewFields)) {
            if (this.validateField(fieldName, field)) {
                fields.push(Object.assign({ name: fieldName }, field));
            }
        }
        this.fields = sortBy(fields, "string");

        useBus(this.env.searchModel, "update", this.render);
    }

    /**
     * @returns {boolean}
     */
    get hideCustomGroupBy() {
        return this.env.searchModel.hideCustomGroupBy || false;
    }

    /**
     * @returns {Object[]}
     */
    get items() {
        return this.env.searchModel.getSearchItems((searchItem) =>
            ["groupBy", "dateGroupBy"].includes(searchItem.type)
        );
    }

    /**
     * @param {string} fieldName
     * @param {Object} field
     * @returns {boolean}
     */
    validateField(fieldName, field) {
        const { sortable, type } = field;
        return fieldName !== "id" && sortable && GROUPABLE_TYPES.includes(type);
    }

    /**
     * @param {Object} param0
     * @param {number} param0.itemId
     * @param {number} [param0.optionId]
     */
    onGroupBySelected({ itemId, optionId }) {
        if (optionId) {
            this.env.searchModel.toggleDateGroupBy(itemId, optionId);
        } else {
            this.env.searchModel.toggleSearchItem(itemId);
        }
    }

    /**
     * @param {string} fieldName
     */
    onAddCustomGroup(fieldName) {
        this.env.searchModel.createNewGroupBy(fieldName);
    }
}

GroupByMenu.components = { CustomGroupByItem, Dropdown, DropdownItem };
GroupByMenu.template = "web.GroupByMenu";
GroupByMenu.defaultProps = {
    showActiveItems: true,
    showCaretDown: false,
};
