/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { ExpressionEditor } from "@web/core/expression_editor/expression_editor";

export class ExpressionEditorDialog extends Component {
    static components = { Dialog, ExpressionEditor };
    static template = "web.ExpressionEditorDialog";
    static props = {
        close: Function,
        expression: String,
        onConfirm: Function,
        resModel: String,
        isDebugMode: { type: Boolean, optional: true },
    };
    static defaultProps = {
        isDebugMode: false,
    };

    setup() {
        this.state = useState({
            expression: this.props.expression,
        });
    }

    get expressionEditorProps() {
        return {
            resModel: this.props.resModel,
            expression: this.state.expression,
            isDebugMode: this.props.isDebugMode,
            update: (expression) => {
                this.state.expression = expression;
            },
        };
    }

    onConfirm() {
        this.props.onConfirm(this.state.expression);
        this.props.close();
    }

    onDiscard() {
        this.props.close();
    }
}
