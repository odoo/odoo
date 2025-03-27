/** @odoo-module **/

import {CustomFilterItem} from "@web/search/filter_menu/custom_filter_item";
import {RecordPicker} from "../../js/RecordPicker.esm";
import {patch} from "@web/core/utils/patch";

/**
 * Patches the CustomFilterItem for owl widgets.
 */
patch(CustomFilterItem.prototype, "web_advanced_search.CustomFilterItem", {
    /**
     * @override
     */
    setup() {
        this._super.apply(this, arguments);
        this.OPERATORS.relational = this.OPERATORS.char;
        this.FIELD_TYPES.many2one = "relational";
        this.FIELD_TYPES.many2many = "relational";
        this.FIELD_TYPES.one2many = "relational";
    },
    /**
     * @override
     */
    setDefaultValue(condition) {
        const fieldType = this.fields[condition.field].type;
        const genericType = this.FIELD_TYPES[fieldType];
        if (genericType === "relational") {
            condition.value = 0;
            condition.displayedValue = "";
            return;
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Add displayed value to preFilters for "relational" types.
     *
     * @override
     */
    onApply() {
        // To avoid the complete override, we patch this.conditions.map()
        const originalMapFn = this.conditions.map;
        const self = this;
        this.conditions.map = function () {
            const preFilters = originalMapFn.apply(this, arguments);
            for (const condition of this) {
                const field = self.fields[condition.field];
                const type = self.FIELD_TYPES[field.type];
                if (type === "relational") {
                    const idx = this.indexOf(condition);
                    const preFilter = preFilters[idx];
                    const operator = self.OPERATORS[type][condition.operator];
                    if (
                        ["=", "!="].includes(operator.symbol) &&
                        operator.value === undefined
                    ) {
                        const descriptionArray = [
                            field.string,
                            operator.description,
                            `"${condition.displayedValue}"`,
                        ];
                        preFilter.description = descriptionArray.join(" ");
                    }
                }
            }
            return preFilters;
        };
        const res = this._super.apply(this, arguments);
        // Restore original map()
        this.conditions.map = originalMapFn;
        return res;
    },
    /**
     * @private
     * @param {Object} condition
     * @param {OwlEvent} ev
     */
    onRelationalChanged(condition, ev) {
        if (ev.detail) {
            condition.value = ev.detail.id;
            condition.displayedValue = ev.detail.display_name;
        }
    },
    onValueChange(condition, ev) {
        if (!ev.target.value) {
            return this.setDefaultValue(condition);
        }
        const field = this.fields[condition.field];
        const type = this.FIELD_TYPES[field.type];
        if (type === "relational") {
            condition.value = ev.target.value;
            condition.displayedValue = ev.target.value;
        } else {
            this._super.apply(this, arguments);
        }
    },
});

patch(CustomFilterItem, "web_advanced_search.CustomFilterItem", {
    components: {
        ...CustomFilterItem.components,
        RecordPicker,
    },
});

export default CustomFilterItem;
