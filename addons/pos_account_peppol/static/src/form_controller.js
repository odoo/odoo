import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { evaluateExpr } from "@web/core/py_js/py";

patch(FormController.prototype, {
    async afterExecuteActionButton(clickParams) {
        await super.afterExecuteActionButton(...arguments);
        if (this.env.inDialog) {
            const buttonContext =
                typeof clickParams.context === "string"
                    ? evaluateExpr(clickParams.context, this.model.root.evalContext)
                    : clickParams.context || {};
            if (buttonContext.reload_form) {
                await this.model.load();
            }
        }
    },
});
