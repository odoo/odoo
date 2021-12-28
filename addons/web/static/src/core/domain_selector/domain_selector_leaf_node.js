/** @odoo-module **/

import { DatePicker, DateTimePicker } from "@web/core/datepicker/datepicker";
import { parseDate, parseDateTime, serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { useModelField } from "@web/core/model_field_selector/model_field_hook";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { registry } from "@web/core/registry";
import { DomainSelectorControlPanel } from "./domain_selector_control_panel";

const { Component } = owl;
const { useRef } = owl.hooks;

const OPERATOR_MAPPING = {
    "=": "=",
    "!=": _lt("is not ="),
    ">": ">",
    ">=": ">=",
    "<": "<",
    "<=": "<=",
    ilike: _lt("contains"),
    "not ilike": _lt("does not contain"),
    in: _lt("in"),
    "not in": _lt("not in"),
    child_of: _lt("child of"),
    parent_of: _lt("parent of"),
    like: _lt("like"),
    "not like": _lt("not like"),
    "=like": _lt("=like"),
    "=ilike": _lt("=ilike"),
    set: _lt("is set"),
    "not set": _lt("is not set"),
};

const BOOLEAN_OPERATOR_MAPPING = {
    "=": _lt("is"),
    "!=": _lt("is not"),
};

function pickOperators(keys) {
    const operators = {};
    for (const key of keys) {
        operators[key] = OPERATOR_MAPPING[key];
    }
    return operators;
}

function getOperatorsFromType(type) {
    let operators = {};

    switch (type) {
        case "boolean":
            operators = { ...BOOLEAN_OPERATOR_MAPPING };
            break;
        case "char":
        case "text":
        case "html":
            operators = pickOperators([
                "=",
                "!=",
                "ilike",
                "not ilike",
                "set",
                "not set",
                "in",
                "not in",
            ]);
            break;
        case "many2many":
        case "one2many":
        case "many2one":
            operators = pickOperators(["=", "!=", "ilike", "not ilike", "set", "not set"]);
            break;
        case "integer":
        case "float":
        case "monetary":
            operators = pickOperators([
                "=",
                "!=",
                ">",
                "<",
                ">=",
                "<=",
                "ilike",
                "not ilike",
                "set",
                "not set",
            ]);
            break;
        case "selection":
            operators = pickOperators(["=", "!=", "set", "not set"]);
            break;
        case "date":
        case "datetime":
            operators = pickOperators(["=", "!=", ">", "<", ">=", "<=", "set", "not set"]);
            break;
        default:
            operators = { ...OPERATOR_MAPPING };
            break;
    }

    return operators;
}

export class DomainSelectorLeafNode extends Component {
    setup() {
        this.inputRef = useRef("input");
        this.modelField = useModelField();
        this.fieldInfo = {
            type: "integer",
            string: "ID",
        };
    }
    async willStart() {
        this.fieldInfo = await this.loadField(this.getFieldFromNode(this.props.node));
    }
    async willUpdateProps(nextProps) {
        this.fieldInfo = await this.loadField(this.getFieldFromNode(nextProps.node));
    }

    get displayedOperator() {
        return OPERATOR_MAPPING[this.props.node.operator] || "?";
    }
    get displayedValue() {
        return this.props.node.operands[1];
    }

    get hasSelectionValues() {
        return ["boolean", "selection"].includes(this.fieldInfo.type);
    }
    get selectionValues() {
        switch (this.fieldInfo.type) {
            case "boolean":
                return [
                    [1, this.env._t("set (true)")],
                    [0, this.env._t("not set (false)")],
                ];
            case "selection":
                return this.fieldInfo.selection;
            default:
                return [];
        }
    }

    get isSetOperator() {
        return (
            ["=", "!="].includes(this.props.node.operator) &&
            typeof this.props.node.operands[1] === "boolean" &&
            this.fieldInfo.type !== "boolean"
        );
    }

    get dateValue() {
        return this.props.node.operands[1]
            ? parseDate(this.props.node.operands[1])
            : luxon.DateTime.local();
    }
    get dateTimeValue() {
        return this.props.node.operands[1]
            ? parseDateTime(this.props.node.operands[1])
            : luxon.DateTime.local();
    }

    isSelectedOperator(operator) {
        return this.isSetOperator
            ? operator === (this.props.node.operator === "=" ? "set" : "not set")
            : operator === this.props.node.operator;
    }
    isSelectedValue(value) {
        if (this.fieldInfo.type === "boolean") {
            return !!value === this.props.node.operands[1];
        }
        return value === this.props.node.operands[1];
    }

    async loadField(fieldName) {
        const chain = await this.modelField.loadChain(this.props.resModel, fieldName);
        if (!chain[chain.length - 1].field && chain.length > 1) {
            return chain[chain.length - 2].field;
        }
        return chain[chain.length - 1].field || {};
    }

    getFieldFromNode(node) {
        return node.operands[0];
    }

    getOperators() {
        const operators = getOperatorsFromType(this.fieldInfo.type);
        if (!(this.props.node.operator in operators)) {
            operators[this.props.node.operator] = this.displayedOperator;
        }
        return operators;
    }

    async onFieldChange(fieldName) {
        const changes = { fieldName };
        const fieldInfo = await this.loadField(fieldName);
        if (fieldInfo && fieldInfo.type !== this.fieldInfo.type) {
            if (fieldInfo.type === "boolean") {
                changes.value = true;
            } else if (fieldInfo.type === "selection") {
                changes.value = fieldInfo.selection[0][0];
            } else if (["float", "integer"].includes(fieldInfo.type)) {
                changes.value = 0;
            } else if (fieldInfo.type === "date") {
                changes.value = serializeDate(luxon.DateTime.utc());
            } else if (fieldInfo.type === "datetime") {
                changes.value = serializeDateTime(luxon.DateTime.utc());
            } else {
                changes.value = "";
            }
        }
        this.props.node.update(changes);
    }
    onOperatorChange(ev) {
        const changes = { operator: ev.target.value };
        if (["set", "not set"].includes(changes.operator)) {
            changes.operator = changes.operator === "set" ? "=" : "!=";
            changes.value = false;
        } else if (["in", "not in"].includes(changes.operator)) {
            changes.value = [];
        } else if (this.isSetOperator || ["in", "not in"].includes(this.props.node.operator)) {
            changes.value = "";
        }
        this.props.node.update(changes);
    }
    onValueChange(ev) {
        let value = ev.target.value;
        if (["integer", "float", "monetary"].includes(this.fieldInfo.type)) {
            value = registry.category("parsers").get(this.fieldInfo.type)(value);
        }
        this.props.node.update({ value });
    }
    onValueSelected(ev) {
        let value = ev.target.value;
        if (this.fieldInfo.type === "boolean") {
            value = value === "1";
        }
        this.props.node.update({ value });
    }
    onAddTagBtnClick() {
        if (this.inputRef.el.value.trim()) {
            const value = Array.from(this.props.node.operands[1]);
            value.push(this.inputRef.el.value);
            this.props.node.update({ value });
            this.inputRef.el.value = "";
        }
    }
    onRemoveTagBtnClick(index) {
        const value = Array.from(this.props.node.operands[1]);
        value.splice(index, 1);
        this.props.node.update({ value });
    }
    onDateValueChange(date) {
        this.props.node.update({
            value: serializeDate(date),
        });
    }
    onDateTimeValueChange(date) {
        this.props.node.update({
            value: serializeDateTime(date.toUTC(0, { keepLocalTime: true })),
        });
    }
}
DomainSelectorLeafNode.template = "web.DomainSelectorLeafNode";
DomainSelectorLeafNode.components = {
    DomainSelectorControlPanel,
    ModelFieldSelector,
    DatePicker,
    DateTimePicker,
};
