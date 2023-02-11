/** @odoo-module */

import { GroupByMenu } from "@web/search/group_by_menu/group_by_menu";
import { getIntervalOptions } from "@web/search/utils/dates";

export class PivotGroupByMenu extends GroupByMenu {
    /**
     * @override
     * @returns {Object[]}
     */
    get items() {
        let items = super.items.filter((i) => !i.custom);
        if (items.length === 0) {
            items = this.fields;
        }

        // Add custom groupbys
        let groupNumber = 1 + Math.max(0, ...items.map(({ groupNumber: n }) => n));
        for (const [fieldName, customGroupBy] of this.props.customGroupBys.entries()) {
            items.push({ ...customGroupBy, name: fieldName, groupNumber: groupNumber++ });
        }

        return items.map((item) => ({
            ...item,
            id: item.id || item.name,
            fieldName: item.fieldName || item.name,
            description: item.description || item.string,
            isActive: false,
            options:
                item.options || ["date", "datetime"].includes(item.type)
                    ? getIntervalOptions()
                    : undefined,
        }));
    }
    /**
     * @override
     * @param {CustomEvent} ev
     */
    onAddCustomGroup(ev) {
        this.trigger("add-custom-group-by", {
            fieldName: ev.detail.fieldName,
            groupId: this.props.cell.groupId,
        });
    }
    /**
     * @override
     * @param {CustomEvent} ev
     */
    onGroupBySelected(ev) {
        const { itemId, optionId } = ev.detail.payload;
        const item = this.items.find(({ id }) => id === itemId);
        // Augment payload data
        Object.assign(ev.detail.payload, {
            fieldName: item.fieldName,
            interval: optionId,
            groupId: this.props.cell.groupId,
        });
    }
}
