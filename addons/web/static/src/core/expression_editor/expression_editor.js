/** @odoo-module **/

import {
    expressionFromExpressionTree,
    expressionTreeFromExpression,
} from "@web/core/expression_tree";
import { TreeEditor } from "@web/core/tree_editor/tree_editor";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";

export class ExpressionEditor extends Component {
    static components = { TreeEditor };
    static template = "web.ExpressionEditor";
    static props = {
        resModel: String,
        expression: String,
        update: Function,
        isDebugMode: { type: Boolean, optional: true },
    };
    static defaultProps = {
        isDebugMode: false,
    };

    setup() {
        this.fieldService = useService("field");
        onWillStart(() => this.onPropsUpdated(this.props));
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps));
    }

    async onPropsUpdated(props) {
        try {
            this.fieldDefs = await this.fieldService.loadFields(props.resModel);
            this.expressionTree = expressionTreeFromExpression(props.expression, {
                getFieldDef: (name) => this.getFieldDef(name),
                distributeNot: props.isDebugMode,
            });
        } catch {
            this.fieldDefs = {};
            this.expressionTree = null;
        }
    }

    getFieldDef(name) {
        if (typeof name !== "string") {
            return null;
        }
        return this.fieldDefs[name] || null;
    }

    onExpressionChange(expression) {
        this.props.update(expression);
    }

    update(expressionTree) {
        const expression = expressionFromExpressionTree(expressionTree, {
            getFieldDef: (name) => this.getFieldDef(name),
        });
        this.props.update(expression);
    }
}
