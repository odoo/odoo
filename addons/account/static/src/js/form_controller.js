import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.props.resModel === "account.move" ) {
            this.fieldService.setTrackedModels(["account.move", "account.move.line"]);
        }
    },
})
