/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

export class AccountMoveSendController extends FormController {

    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name === "action_cancel" && this.model.root.isNew) {
            clickParams.special = "cancel";
        }
        return super.beforeExecuteActionButton(...arguments);
    }
}

export const AccountMoveSend = {
    ...formView,
    Controller: AccountMoveSendController,
};

registry.category("views").add("account_move_send_form", AccountMoveSend);
