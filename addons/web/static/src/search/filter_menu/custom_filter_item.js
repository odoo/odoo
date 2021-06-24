/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { localization } from "@web/core/l10n/localization";
import { parseDate, parseDateTime } from "@web/core/l10n/dates";
import { parseFloat, parseInteger, parsePercentage } from "@web/core/l10n/numbers";

const { Component, hooks } = owl;
const { useState } = hooks;

const { DateTime } = luxon;

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
        { symbol: "=", description: _lt("is true"), value: true },
        { symbol: "!=", description: _lt("is false"), value: true },
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

function getParser(type) {
    switch (type) {
        case "date":
            return parseDate;
        case "datetime":
            return parseDateTime;
        case "float":
            return parseFloat;
        case "percentage":
            return parsePercentage;
        case "integer":
            return parseInteger;
        default:
            return (str) => str;
    }
}

export class CustomFilterItem extends Component {
    setup() {
        this.conditions = useState([]);
        // Format, filter and sort the fields props
        this.fields = Object.values(this.env.searchModel.searchViewFields)
            .filter((field) => this._validateField(field))
            .concat({ string: "ID", type: "id", name: "id" })
            .sort(({ string: a }, { string: b }) => (a > b ? 1 : a < b ? -1 : 0));

        // Give access to constants variables to the template.
        this.DECIMAL_POINT = localization.decimalPoint;
        this.OPERATORS = FIELD_OPERATORS;
        this.FIELD_TYPES = FIELD_TYPES;

        // Add first condition
        this.addNewCondition();
    }

    //---------------------------------------------------------------------
    // Private
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
    _validateField(field) {
        return (
            !field.deprecated && field.searchable && FIELD_TYPES[field.type] && field.name !== "id"
        );
    }

    /**
     * @param {Object} condition
     */
    setDefaultValue(condition) {
        const fieldType = this.fields[condition.field].type;
        const genericType = FIELD_TYPES[fieldType];
        const operator = FIELD_OPERATORS[genericType][condition.operator];
        // Logical value
        switch (genericType) {
            case "id":
            case "number":
                condition.value = 0;
                break;
            case "date":
                condition.value = [DateTime.local()];
                if (operator.symbol === "between") {
                    condition.value.push(DateTime.local());
                }
                break;
            case "datetime":
                condition.value = [DateTime.fromFormat("00:00:00", "hh:mm:ss")];
                if (operator.symbol === "between") {
                    condition.value.push(DateTime.fromFormat("23:59:59", "hh:mm:ss"));
                }
                break;
            case "selection":
                const [firstValue] = this.fields[condition.field].selection[0];
                condition.value = firstValue;
                break;
            default:
                condition.value = "";
        }
        // Displayed value
        if (["float", "monetary"].includes(fieldType)) {
            condition.displayedValue = `0${this.DECIMAL_POINT}0`;
        } else {
            condition.displayedValue = String(condition.value);
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
            const type = this.FIELD_TYPES[field.type];
            const operator = this.OPERATORS[type][condition.operator];
            const descriptionArray = [field.string, operator.description.toString()];
            const domainArray = [];
            let domainValue;
            // Field type specifics
            if ("value" in operator) {
                domainValue = [operator.value];
                // No description to push here
            } else if (["date", "datetime"].includes(type)) {
                /** @todo rework datepicker before that */
                const parser = getParser(type);
                domainValue = condition.value.map((val) => parser(val, { timezone: false }));
                const dateValue = condition.value.map((val) => parser(val, { timezone: true }));
                const dateDescription = dateValue.map((val) => {
                    if (type === "datetime") {
                        return val.toJSON();
                    }
                    return val.toFormat("yyyy-MM-dd");
                });
                descriptionArray.push(`"${dateDescription.join(" " + this.env._t("and") + " ")}"`);
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
     * @param {OwlEvent} ev
     */
    onDateChanged(condition, valueIndex, ev) {
        condition.value[valueIndex] = ev.detail.date;
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
    onValueInput(condition, ev) {
        if (!ev.target.value) {
            return this.setDefaultValue(condition);
        }
        let { type } = this.fields[condition.field];
        if (type === "id") {
            type = "integer";
        }
        if (FIELD_TYPES[type] === "number") {
            try {
                // Write logical value into the 'value' property
                condition.value = getParser(type)(ev.target.value);
                // Write displayed value in the input and 'displayedValue' property
                condition.displayedValue = ev.target.value;
            } catch (err) {
                // Parsing error: reverts to previous value
                ev.target.value = condition.displayedValue;
            }
        } else {
            condition.value = condition.displayedValue = ev.target.value;
        }
    }
}

// CustomFilterItem.components = { DatePicker, DateTimePicker };

CustomFilterItem.template = "web.CustomFilterItem";
