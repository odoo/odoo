/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

import { startRegistration } from "../../lib/simplewebauthn.js"

export class PassKeyNameFormController extends FormController {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
    }

    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name === "make_key") {
            const name = document.querySelector("div[name='name'].o_field_widget input").value
            if(name.length > 0) {
                const serverOptions = await this.rpc("/auth/passkey/start-registration");
                const registration = await startRegistration(serverOptions).catch(e => console.error(e));
                // In case the user cancel the passkey browser check, just interrupt.
                if(!registration) return false;
                const verification = await this.rpc("/auth/passkey/verify-registration", { registration });
                clickParams.args = JSON.stringify([verification.credentialId, verification.credentialPublicKey]);
            }
        }
        return super.beforeExecuteActionButton(...arguments);
    }
}

export const PassKeyNameFormView = {
    ...formView,
    Controller: PassKeyNameFormController,
};

registry.category("views").add("auth_passkey_key_name_view_form", PassKeyNameFormView);
