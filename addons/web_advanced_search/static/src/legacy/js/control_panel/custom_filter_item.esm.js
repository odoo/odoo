/** @odoo-module **/

import CustomFilterItem from "web.CustomFilterItem";
import {RecordPicker} from "../../../js/RecordPicker.esm";
import {patch} from "@web/core/utils/patch";

/**
 * Patches the CustomFilterItem for legacy widgets.
 *
 * Tree views still use this old legacy widget, so we need to patch it.
 * This is likely to disappear in 17.0
 */
patch(CustomFilterItem.prototype, "web_advanced_search.legacy.CustomFilterItem", {
    /**
     * Ideally we'd want this in setup, but CustomFilterItem does its initialization
     * in the constructor, which can't be patched.
     *
     * Doing it here works just as well.
     *
     * @override
     */
    async willStart() {
        this.OPERATORS.relational = this.OPERATORS.char;
        this.FIELD_TYPES.many2one = "relational";
        this.FIELD_TYPES.many2many = "relational";
        this.FIELD_TYPES.one2many = "relational";
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _setDefaultValue(condition) {
        const res = this._super(...arguments);
        const fieldType = this.fields[condition.field].type;
        const genericType = this.FIELD_TYPES[fieldType];
        if (genericType === "relational") {
            condition.value = 0;
            condition.displayedValue = "";
        }
        return res;
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
                    const descriptionArray = [
                        field.string,
                        operator.description,
                        `"${condition.displayedValue}"`,
                    ];
                    preFilter.description = descriptionArray.join(" ");
                }
            }
            return preFilters;
        };
        const res = this._super(...arguments);
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
});

patch(CustomFilterItem, "web_advanced_search.legacy.CustomFilterItem", {
    components: {
        ...CustomFilterItem.components,
        RecordPicker,
    },
});

export default CustomFilterItem;
