import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { getExpressionDisplayedOperators } from "@web/core/expression_editor/expression_editor_operator_editor";
import { _t } from "@web/core/l10n/translation";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { condition } from "@web/core/tree_editor/condition_tree";
import { expressionFromTree } from "@web/core/tree_editor/expression_from_tree";
import { TreeEditor } from "@web/core/tree_editor/tree_editor";
import { getOperatorEditorInfo } from "@web/core/tree_editor/tree_editor_operator_editor";
import { getDefaultValue } from "@web/core/tree_editor/tree_editor_value_editors";
import { treeFromExpression } from "@web/core/tree_editor/tree_from_expression";
import { getDefaultPath } from "@web/core/tree_editor/utils";

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
        this.filteredFields = Object.fromEntries(
            Object.entries(props.fields).filter(([_, fieldDef]) => fieldDef.type !== "properties")
        );
        try {
            this.tree = treeFromExpression(props.expression, {
                getFieldDef: (name) => this.getFieldDef(name, props),
                distributeNot: !this.isDebugMode,
                generateSmartDates: false,
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

    getDefaultCondition() {
        const defaultPath = getDefaultPath(this.filteredFields);
        const fieldDef = this.filteredFields[defaultPath];
        const operator = getExpressionDisplayedOperators(fieldDef)[0];
        const value = getDefaultValue(fieldDef, operator);
        return condition(fieldDef.name, operator, value);
    }

    getDefaultOperator(fieldDef) {
        return getExpressionDisplayedOperators(fieldDef)[0];
    }

    getOperatorEditorInfo(fieldDef) {
        const operators = getExpressionDisplayedOperators(fieldDef);
        return getOperatorEditorInfo(operators, fieldDef);
    }

    getPathEditorInfo(resModel, defaultCondition) {
        if (resModel !== this.props.resModel) {
            throw new Error(
                `Expression editor doesn't support tree as value so resModel has to be props.resModel`
            );
        }
        return {
            component: ModelFieldSelector,
            extractProps: ({ value, update }) => ({
                path: value,
                update,
                resModel: this.props.resModel,
                readonly: false,
                filter: (fieldDef) => fieldDef.name in this.filteredFields,
                showDebugInput: false,
                followRelations: false,
                isDebugMode: this.isDebugMode,
            }),
            isSupported: (value) => [0, 1].includes(value) || value in this.filteredFields,
            // by construction, all values received by the path editor are O/1 or a field (name) in this.props.fields.
            // (see _leafFromAST in condition_tree.js)
            stringify: (value) => this.props.fields[value].string,
            defaultValue: () => defaultCondition.path,
            message: _t("Field properties not supported"),
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
            generateSmartDates: false,
        });
        this.props.update(expression);
    }
}
