/** @odoo-module **/

import { DatePicker, DateTimePicker } from "@web/core/datepicker/datepicker";
import { Domain } from "@web/core/domain";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { Component, useState } from "@odoo/owl";

const { DateTime } = luxon;

const formatters = registry.category("formatters");
const parsers = registry.category("parsers");

const FIELD_TYPES = {
    boolean: "boolean",
    char: "char",
    date: "date",
    datetime: "datetime",
    float: "number",
    id: "id",
    integer: "number",
    html: "char",
    many2many: "char",
    many2one: "char",
    monetary: "number",
    one2many: "char",
    text: "char",
    selection: "selection",
};

// FilterMenu parameters
const FIELD_OPERATORS = {
    boolean: [
        { symbol: "=", description: _lt("is Yes"), value: true },
        { symbol: "!=", description: _lt("is No"), value: true },
    ],
    char: [
        { symbol: "ilike", description: _lt("contains") },
        { symbol: "not ilike", description: _lt("doesn't contain") },
        { symbol: "=", description: _lt("is equal to") },
        { symbol: "!=", description: _lt("is not equal to") },
        { symbol: "!=", description: _lt("is set"), value: false },
        { symbol: "=", description: _lt("is not set"), value: false },
    ],
    date: [
        { symbol: "=", description: _lt("is equal to") },
        { symbol: "!=", description: _lt("is not equal to") },
        { symbol: ">", description: _lt("is after") },
        { symbol: "<", description: _lt("is before") },
        { symbol: ">=", description: _lt("is after or equal to") },
        { symbol: "<=", description: _lt("is before or equal to") },
        { symbol: "between", description: _lt("is between") },
        { symbol: "!=", description: _lt("is set"), value: false },
        { symbol: "=", description: _lt("is not set"), value: false },
    ],
    datetime: [
        { symbol: "between", description: _lt("is between") },
        { symbol: "=", description: _lt("is equal to") },
        { symbol: "!=", description: _lt("is not equal to") },
        { symbol: ">", description: _lt("is after") },
        { symbol: "<", description: _lt("is before") },
        { symbol: ">=", description: _lt("is after or equal to") },
        { symbol: "<=", description: _lt("is before or equal to") },
        { symbol: "!=", description: _lt("is set"), value: false },
        { symbol: "=", description: _lt("is not set"), value: false },
    ],
    id: [{ symbol: "=", description: _lt("is") }],
    number: [
        { symbol: "=", description: _lt("is equal to") },
        { symbol: "!=", description: _lt("is not equal to") },
        { symbol: ">", description: _lt("greater than") },
        { symbol: "<", description: _lt("less than") },
        { symbol: ">=", description: _lt("greater than or equal to") },
        { symbol: "<=", description: _lt("less than or equal to") },
        { symbol: "!=", description: _lt("is set"), value: false },
        { symbol: "=", description: _lt("is not set"), value: false },
    ],
    selection: [
        { symbol: "=", description: _lt("is") },
        { symbol: "!=", description: _lt("is not") },
        { symbol: "!=", description: _lt("is set"), value: false },
        { symbol: "=", description: _lt("is not set"), value: false },
    ],
};

function parseField(field, value) {
    if (FIELD_TYPES[field.type] === "char") {
        return value;
    }
    const type = field.type === "id" ? "integer" : field.type;
    const parse = parsers.contains(type) ? parsers.get(type) : (v) => v;
    return parse(value);
}

function formatField(field, value) {
    if (FIELD_TYPES[field.type] === "char") {
        return value;
    }
    const type = field.type === "id" ? "integer" : field.type;
    const format = formatters.contains(type) ? formatters.get(type) : (v) => v;
    return format(value, { digits: field.digits });
}

export class CustomFilterItem extends Component {
    setup() {
        this.conditions = useState([]);
        // Format, filter and sort the fields props
        this.fields = Object.values(this.env.searchModel.searchViewFields)
            .filter((field) => this.validateField(field))
            .concat({ string: "ID", type: "id", name: "id" })
            .sort(({ string: a }, { string: b }) => (a > b ? 1 : a < b ? -1 : 0));

        // Give access to constants variables to the template.
        this.OPERATORS = FIELD_OPERATORS;
        this.FIELD_TYPES = FIELD_TYPES;

        // Add first condition
        this.addNewCondition();
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    /**
     * Populate the conditions list with a new condition having as properties:
     * - the last condition or the first available field
     * - the last condition or the first available operator
     * - a null or empty array value
     */
    addNewCondition() {
        const lastCondition = [...this.conditions].pop();
        const condition = lastCondition
            ? Object.assign({}, lastCondition)
            : {
                  field: 0,
                  operator: 0,
              };
        this.setDefaultValue(condition);
        this.conditions.push(condition);
    }

    /**
     * @param {Object} field
     * @returns {boolean}
     */
    validateField(field) {
        return (
            !field.deprecated && field.searchable && FIELD_TYPES[field.type] && field.name !== "id"
        );
    }

    /**
     * @param {Object} condition
     */
    setDefaultValue(condition) {
        const field = this.fields[condition.field];
        const genericType = FIELD_TYPES[field.type];
        const operator = FIELD_OPERATORS[genericType][condition.operator];
        // Logical value
        switch (genericType) {
            case "id":
            case "number": {
                condition.value = 0;
                break;
            }
            case "date":
            case "datetime": {
                condition.value = [DateTime.local()];
                if (operator.symbol === "between") {
                    condition.value.push(DateTime.local());
                }
                if (genericType === "datetime") {
                    condition.value[0] = condition.value[0].set({ hour: 0, minute: 0, second: 0 });
                    if (operator.symbol === "between") {
                        condition.value[1] = condition.value[1].set({
                            hour: 23,
                            minute: 59,
                            second: 59,
                        });
                    }
                }
                break;
            }
            case "selection": {
                const [firstValue] = this.fields[condition.field].selection[0];
                condition.value = firstValue;
                break;
            }
            default: {
                condition.value = "";
            }
        }
        // Displayed value (no needed for dates: they are handled by the DatePicker component)
        if (!["date", "datetime"].includes(field.type)) {
            condition.displayedValue = formatField(field, condition.value);
        }
    }

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    /**
     * Convert all conditions to prefilters.
     */
    onApply() {
        const preFilters = this.conditions.map((condition) => {
            const field = this.fields[condition.field];
            const genericType = this.FIELD_TYPES[field.type];
            const operator = this.OPERATORS[genericType][condition.operator];
            const descriptionArray = [field.string, operator.description.toString()];
            const domainArray = [];
            let domainValue;
            // Field type specifics
            if ("value" in operator) {
                domainValue = [operator.value];
                // No description to push here
            } else if (["date", "datetime"].includes(genericType)) {
                const serialize = genericType === "date" ? serializeDate : serializeDateTime;
                domainValue = condition.value.map(serialize);
                descriptionArray.push(
                    `"${condition.value
                        .map((val) => formatField(field, val))
                        .join(" " + this.env._t("and") + " ")}"`
                );
            } else {
                domainValue = [condition.value];
                descriptionArray.push(`"${condition.value}"`);
            }
            // Operator specifics
            if (operator.symbol === "between") {
                domainArray.push(
                    [field.name, ">=", domainValue[0]],
                    [field.name, "<=", domainValue[1]]
                );
            } else {
                domainArray.push([field.name, operator.symbol, domainValue[0]]);
            }
            const preFilter = {
                description: descriptionArray.join(" "),
                domain: new Domain(domainArray).toString(),
                type: "filter",
            };
            return preFilter;
        });

        this.env.searchModel.createNewFilters(preFilters);

        // remove conditions
        while (this.conditions.length) {
            this.conditions.pop();
        }

        this.addNewCondition();
    }

    /**
     * @param {Object} condition
     * @param {number} valueIndex
     * @param {Date} ev
     */
    onDateTimeChanged(condition, valueIndex, date) {
        condition.value[valueIndex] = date;
    }

    /**
     * @param {Object} condition
     * @param {Event} ev
     */
    onFieldSelect(condition, ev) {
        Object.assign(condition, {
            field: ev.target.selectedIndex,
            operator: 0,
        });
        this.setDefaultValue(condition);
    }

    /**
     * @param {Object} condition
     * @param {Event} ev
     */
    onOperatorSelect(condition, ev) {
        condition.operator = ev.target.selectedIndex;
        this.setDefaultValue(condition);
    }

    /**
     * @param {Object} condition
     */
    onRemoveCondition(conditionIndex) {
        this.conditions.splice(conditionIndex, 1);
    }

    /**
     * @param {Object} condition
     * @param {Event} ev
     */
    onValueChange(condition, ev) {
        if (!ev.target.value) {
            return this.setDefaultValue(condition);
        }
        const field = this.fields[condition.field];
        try {
            const parsed = parseField(field, ev.target.value);
            const formatted = formatField(field, parsed);
            // Only updates values if it can be correctly parsed and formatted.
            condition.value = parsed;
            condition.displayedValue = formatted;
        } catch (_err) {
            // Parsing error: nothing is done
        }
        // Only reset the target's value if it is not a selection field.
        if (field.type !== "selection") {
            ev.target.value = condition.displayedValue;
        }
    }
}

CustomFilterItem.components = { DatePicker, DateTimePicker, Dropdown };
CustomFilterItem.template = "web.CustomFilterItem";
