import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    async afterExecuteActionButton(clickParams) {
        await super.afterExecuteActionButton(...arguments);
        if (this.env.inDialog && clickParams.name === "action_pdp_annuaire_lookup") {
            await this.model.load();
        }
    },
});
