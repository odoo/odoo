import { FormController } from "@web/views/form/form_controller";

export class StripeFormController extends FormController {
    async beforeExecuteActionButton(clickParams) {
        const record = this.model.root;
        if (record.data.code === "stripe" && clickParams.name == "action_stripe_create_webhook") {
            await record.model._askChanges();
            const changes = record._getChanges();
            const fieldName = "stripe_webhook_secret";
            if (
                (fieldName in changes && changes[fieldName] === false) ||
                record.data[fieldName] === false
            ) {
                record.update({ stripe_webhook_secret: " " });
            }
        }
        return super.beforeExecuteActionButton(clickParams);
    }
}
