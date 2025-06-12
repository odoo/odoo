import { Component } from "@odoo/owl";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { localization } from "@web/core/l10n/localization";
import { sortBy } from "@web/core/utils/arrays";
import { useBus } from "@web/core/utils/hooks";
import { CustomGroupByItem } from "@web/search/custom_group_by_item/custom_group_by_item";
import { PropertiesGroupByItem } from "@web/search/properties_group_by_item/properties_group_by_item";
import { getIntervalOptions } from "@web/search/utils/dates";
import { FACET_ICONS, GROUPABLE_TYPES } from "@web/search/utils/misc";

export class PivotHeader extends Component {
    static template = "web.PivotHeader";
    static components = {
        CustomGroupByItem,
        Dropdown,
        CheckboxItem,
        PropertiesGroupByItem,
    };
    static defaultProps = {
        isInHead: false,
        isXAxis: false,
        showCaretDown: false,
    };
    static props = {
        cell: Object,
        isInHead: { type: Boolean, optional: true },
        isXAxis: { type: Boolean, optional: true },
        customGroupBys: Object,
        onAddCustomGroupBy: Function,
        onItemSelected: Function,
        onClick: Function,
        slots: { optional: true },
    };

    setup() {
        this.icon = FACET_ICONS.groupBy;
        const fields = [];
        for (const [fieldName, field] of Object.entries(this.env.searchModel.searchViewFields)) {
            if (this.validateField(fieldName, field)) {
                fields.push(Object.assign({ name: fieldName }, field));
            }
        }
        this.fields = sortBy(fields, "string");
        this.l10n = localization;
        this.dropdownState = useDropdownState();

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
        let items = this.env.searchModel.getSearchItems(
            (searchItem) =>
                ["groupBy", "dateGroupBy"].includes(searchItem.type) && !searchItem.custom
        );
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
                item.options ||
                (["date", "datetime"].includes(item.type) ? getIntervalOptions() : undefined),
        }));
    }

    get cell() {
        return this.props.cell;
    }

    /**
     * Retrieve the padding of a left header.
     * @returns {Number} Padding
     */
    get padding() {
        return 5 + this.cell.indent * 30;
    }

    /**
     * @param {string} fieldName
     * @param {Object} field
     * @returns {boolean}
     */
    validateField(fieldName, field) {
        const { groupable, type } = field;
        return groupable && fieldName !== "id" && GROUPABLE_TYPES.includes(type);
    }

    /**
     * @override
     * @param {Object} param0
     * @param {number} param0.itemId
     * @param {number} [param0.optionId]
     */
    onGroupBySelected({ itemId, optionId }) {
        // Here, we purposely do not call super.onGroupBySelected as we don't want
        // to change the group-by on the model, only inside the pivot
        const item = this.items.find(({ id }) => id === itemId);
        this.props.onItemSelected({
            itemId,
            optionId,
            fieldName: item.fieldName,
            interval: optionId,
            groupId: this.cell.groupId,
        });
    }

    /**
     * @param {string} fieldName
     */
    onAddCustomGroup(fieldName) {
        this.props.onAddCustomGroupBy(fieldName);
    }

    /**
     * @param {Event} event
     */
    onClick(event) {
        if (this.cell.isLeaf && !this.cell.isFolded) {
            this.dropdownState.open();
        }
        this.props.onClick();
    }
}
