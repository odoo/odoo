/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { getExpressionDisplayedOperators } from "@web/core/expression_editor/expression_editor_operator_editor";
import {
    condition,
    expressionFromTree,
    treeFromExpression,
} from "@web/core/tree_editor/condition_tree";
import { TreeEditor } from "@web/core/tree_editor/tree_editor";
import { getOperatorEditorInfo } from "@web/core/tree_editor/tree_editor_operator_editor";
import { getDefaultValue } from "@web/core/tree_editor/tree_editor_value_editors";
import { getDefaultPath } from "@web/core/tree_editor/utils";

function getDefaultCondition(fieldDefs) {
    const defaultPath = getDefaultPath(fieldDefs);
    const fieldDef = fieldDefs[defaultPath];
    const operator = getExpressionDisplayedOperators(fieldDef)[0];
    const value = getDefaultValue(fieldDef, operator);
    return condition(fieldDef.name, operator, value);
}

class ExpressionEditorFieldSelector extends Component {
    static template = "web.ExpressionEditorFieldSelector";
    static props = {
        value: [String, { value: 1 }, { value: 0 }],
        update: Function,
        fields: Object,
    };
}

export class ExpressionEditor extends Component {
    static template = "web.ExpressionEditor";
    static components = { TreeEditor };
    static props = {
        resModel: String,
        fields: Object,
        expression: String,
        update: Function,
    };

    setup() {
        onWillStart(() => this.onPropsUpdated(this.props));
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps));
    }

    async onPropsUpdated(props) {
        this.defaultCondition = getDefaultCondition(props.fields);
        try {
            this.tree = treeFromExpression(props.expression, {
                getFieldDef: (name) => this.getFieldDef(name, props),
                distributeNot: !this.isDebugMode,
            });
        } catch {
            this.tree = null;
        }
    }

    getFieldDef(name, props = this.props) {
        if (typeof name === "string") {
            return props.fields[name] || null;
        }
        return null;
    }

    getDefaultOperator(fieldDef) {
        return getExpressionDisplayedOperators(fieldDef)[0];
    }

    getOperatorEditorInfo(node) {
        const fieldDef = this.getFieldDef(node.path);
        const operators = getExpressionDisplayedOperators(fieldDef);
        return getOperatorEditorInfo(operators);
    }

    getPathEditorInfo() {
        return {
            component: ExpressionEditorFieldSelector,
            extractProps: ({ value, update }) => ({
                value,
                update,
                fields: this.props.fields,
            }),
            isSupported: (value) => [0, 1].includes(value) || this.getFieldDef(value),
            // by construction, all values received by the path editor will be supported.
        };
    }

    get isDebugMode() {
        return !!this.env.debug;
    }

    onExpressionChange(expression) {
        this.props.update(expression);
    }

    resetExpression() {
        this.props.update("True");
    }

    update(tree) {
        const expression = expressionFromTree(tree, {
            getFieldDef: (name) => this.getFieldDef(name),
        });
        this.props.update(expression);
    }
}
