import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { evaluateExpr } from "@web/core/py_js/py";
import { floatField, FloatField } from "@web/views/fields/float/float_field";
import { monetaryField, MonetaryField } from "@web/views/fields/monetary/monetary_field";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const fieldRegistry = registry.category("fields");

class StockActionField extends Component {
    static props = {
        ...FloatField.props,
        ...MonetaryField.props,
        actionName: { type: String, optional: false },
        actionContext: { type: String, optional: true },
    };
    static components = {
        FloatField,
        MonetaryField,
    }
    static template = "stock.actionField";

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.fieldType = this.props.record.fields[this.props.name].type;
    }
    
    extractProps () {
        const keysToRemove = ["actionName", "actionContext"];
        return Object.fromEntries(
         Object.entries(this.props).filter(([prop]) => !keysToRemove.includes(prop))
       );
    }

    _onClick(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        // Get the action name from props.options
        const actionName = this.props.actionName;
        const actionContext = evaluateExpr(this.props.actionContext, this.props.record.evalContext);

        // const action = this.orm.call(this.props.record.resModel, actionName, this.props.record.resId);
        // Use the action service to perform the action
        this.actionService.doAction(actionName, {
            additionalContext: { ...actionContext, ...this.props.record.context },
        });
    }
}

const stockActionField = {
    ...floatField,
    ...monetaryField,
    component: StockActionField,
    supportedOptions: [
        ...floatField.supportedOptions,
        ...monetaryField.supportedOptions,
        {
            label: _t("Action Name"),
            name: "action_name",
            type: "string",
        },
    ],
    extractProps: (...args) => {
        const [{ context, fieldType, options }] = args;
        const action_props = {
            actionName: options.action_name,
            actionContext: context,
        }
        let props = {...action_props}
        if (fieldType === "monetary") {
            props = { ...action_props, ...monetaryField.extractProps(...args) };
        } else if (fieldType === "float") {
            props = { ...action_props, ...floatField.extractProps(...args) };
        };
        return props;
    },
};

fieldRegistry.add("stock_action_field", stockActionField);
