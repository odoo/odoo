/** @odoo-module **/

import { evaluateExpr } from "@web/core/py_js/py";
import { formatAST, toPyValue } from "@web/core/py_js/py_utils";
import { registry } from "@web/core/registry";

import { Component } from "@odoo/owl";

const dsf = registry.category("domain_selector/fields");
const dso = registry.category("domain_selector/operator");

export class DomainSelectorSelectionField extends Component {
    get options() {
        return [
            [false, ""],
            ...this.props.field.selection.filter((option) => !this.props.value.includes(option[0])),
        ];
    }

    get formattedValue() {
        const ast = toPyValue(this.props.value);
        return formatAST(ast);
    }

    onChange(ev) {
        this.props.update({ value: ev.target.value });
    }

    onChangeMulti(ev) {
        this.props.update({ value: evaluateExpr(ev.target.value) });
    }
}
Object.assign(DomainSelectorSelectionField, {
    template: "web.DomainSelectorSelectionField",

    onDidTypeChange(field) {
        return { value: field.selection[0][0] };
    },
    getOperators() {
        return ["=", "!=", "set", "not set"].map((key) => dso.get(key));
    },
});

dsf.add("selection", DomainSelectorSelectionField);
