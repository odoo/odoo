import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    async afterExecuteActionButton(clickParams) {
        await super.afterExecuteActionButton(...arguments);
        if (this.env.inDialog && clickParams.name === "action_pos_check_peppol_endpoint") {
            await this.model.load();
        }
    },
});
