/** @odoo-module **/

import { CustomGroupByItem } from "./custom_group_by_item";
import { FACET_ICONS, GROUPABLE_TYPES } from "../utils/misc";

const { Component } = owl;

export class GroupByMenu extends Component {
    setup() {
        this.icon = FACET_ICONS.groupBy;
        this.fields = [];
        for (const [fieldName, field] of Object.entries(this.env.searchModel.searchViewFields)) {
            if (this.validateField(fieldName, field)) {
                this.fields.push(Object.assign({ name: fieldName }, field));
            }
        }
        this.fields.sort(({ string: a }, { string: b }) => (a > b ? 1 : a < b ? -1 : 0));
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
}

GroupByMenu.components = { CustomGroupByItem };
GroupByMenu.template = "web.GroupByMenu";
