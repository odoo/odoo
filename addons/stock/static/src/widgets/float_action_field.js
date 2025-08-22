import { _t } from "@web/core/l10n/translation";
import { evaluateExpr } from "@web/core/py_js/py";
import { floatField, FloatField } from "@web/views/fields/float/float_field";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const fieldRegistry = registry.category("fields");

class StockFloatActionField extends FloatField {
    static template = "stock.floatActionField";
    static props = {
        ...FloatField.props,
        actionName: { type: String, optional: false },
        actionContext: { type: String, optional: true },
    };

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
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
            additionalContext: actionContext,
        });
    }
}

const stockFloatActionField = {
    ...floatField,
    component: StockFloatActionField,
    supportedOptions: [
        ...floatField.supportedOptions,
        {
            label: _t("Action Name"),
            name: "actionName",
            type: "string",
        },
    ],
    extractProps: (...args) => {
        const [{ context, options }] = args;
        return {
            ...floatField.extractProps(...args),
            actionName: options.actionName,
            actionContext: context,
        };
    },
};

fieldRegistry.add("stock_float_action_field", stockFloatActionField);
