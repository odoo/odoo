/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { startRegistration } from "../../lib/simplewebauthn.js"

export class PassKeyNameFormController extends FormController {
    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name === "make_key") {
            const name = document.querySelector("div[name='name'].o_field_widget input").value
            if(name.length > 0) {
                const serverOptions = this.props.context.registration;
                const registration = await startRegistration(serverOptions).catch(e => console.error(e));
                // In case the user cancelled the passkey browser check, just interrupt.
                if(!registration) return false;
                clickParams.args = JSON.stringify([registration]);
            }
        }
        return super.beforeExecuteActionButton(...arguments);
    }
}

export const PassKeyNameFormView = {
    ...formView,
    Controller: PassKeyNameFormController,
};

registry.category("views").add("auth_passkey_key_create_view_form", PassKeyNameFormView);
