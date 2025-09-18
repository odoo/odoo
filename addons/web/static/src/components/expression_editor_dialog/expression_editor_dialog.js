// @ts-check

/** @module @web/components/expression_editor_dialog/expression_editor_dialog - Modal dialog for editing Python expressions with validation preview */

import { Component, useRef, useState } from "@odoo/owl";
import { ExpressionEditor } from "@web/components/expression_editor/expression_editor";
import { _t } from "@web/core/l10n/translation";
import { evaluateExpr } from "@web/core/py_js/py";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/services/user";
import { Dialog } from "@web/ui/dialog/dialog";

export class ExpressionEditorDialog extends Component {
    static components = { Dialog, ExpressionEditor };
    static template = "web.ExpressionEditorDialog";
    static props = {
        close: Function,
        resModel: String,
        fields: Object,
        expression: String,
        onConfirm: Function,
    };

    setup() {
        this.notification = useService("notification");
        this.state = useState({
            expression: this.props.expression,
        });
        /** @type {{ el: HTMLButtonElement | null }} */
        this.confirmButtonRef = useRef("confirm");
    }

    get expressionEditorProps() {
        return {
            resModel: this.props.resModel,
            fields: this.props.fields,
            expression: this.state.expression,
            update: (expression) => {
                this.state.expression = expression;
            },
        };
    }

    makeDefaultRecord() {
        const record = {};
        for (const [name, { type }] of Object.entries(this.props.fields)) {
            switch (type) {
                case "integer":
                case "float":
                case "monetary":
                    record[name] = name === "id" ? false : 0;
                    break;
                case "one2many":
                case "many2many":
                    record[name] = [];
                    break;
                default:
                    record[name] = false;
            }
        }
        return record;
    }

    async onConfirm() {
        /** @type {HTMLButtonElement} */ (this.confirmButtonRef.el).disabled = true;
        const record = this.makeDefaultRecord();
        const evalContext = { ...user.context, ...record };
        try {
            evaluateExpr(this.state.expression, evalContext);
        } catch {
            if (this.confirmButtonRef.el) {
                /** @type {HTMLButtonElement} */ (this.confirmButtonRef.el).disabled =
                    false;
            }
            this.notification.add(_t("Expression is invalid. Please correct it"), {
                type: "danger",
            });
            return;
        }
        this.props.onConfirm(this.state.expression);
        this.props.close();
    }

    onDiscard() {
        this.props.close();
    }
}
