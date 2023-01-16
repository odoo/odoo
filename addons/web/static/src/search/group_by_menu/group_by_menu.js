/** @odoo-module **/

import { CustomGroupByItem } from "./custom_group_by_item";
import { FACET_ICONS, GROUPABLE_TYPES } from "../utils/misc";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { sortBy } from "@web/core/utils/arrays";
import { useBus } from "@web/core/utils/hooks";
import { SearchDropdownItem } from "@web/search/search_dropdown_item/search_dropdown_item";

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
     * @param {CustomEvent} ev
     */
    onGroupBySelected(ev) {
        const { itemId, optionId } = ev.detail.payload;
        if (optionId) {
            this.env.searchModel.toggleDateGroupBy(itemId, optionId);
        } else {
            this.env.searchModel.toggleSearchItem(itemId);
        }
    }

    /**
     * @param {CustomEvent} ev
     */
    onAddCustomGroup(ev) {
        const { fieldName } = ev.detail;
        this.env.searchModel.createNewGroupBy(fieldName);
    }
}

GroupByMenu.components = { CustomGroupByItem, DropdownItem: SearchDropdownItem };
GroupByMenu.template = "web.GroupByMenu";
GroupByMenu.defaultProps = {
    showActiveItems: true,
    showCaretDown: false,
};
