/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { startAuthentication } from "../../lib/simplewebauthn.js";

export class PassKeyIdentityCheckFormController extends FormController {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
    }

    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        if (
            clickParams.name === "run_check" &&
            this.model.root.data.auth_method == "passkey"
        ) {
            const serverOptions = await this.rpc("/auth/passkey/start-auth");
            const auth = await startAuthentication(serverOptions).catch(e => console.log(e));
            // In case the user cancelled the passkey browser check, just interrupt.
            if(!auth) return false;
            clickParams.args = JSON.stringify([auth]);
        }
        return super.beforeExecuteActionButton(...arguments);
    }
}

export const PassKeyIdentityCheckFormView = {
    ...formView,
    Controller: PassKeyIdentityCheckFormController,
};

registry.category("views").add("auth_passkey_identity_check_view_form", PassKeyIdentityCheckFormView);
