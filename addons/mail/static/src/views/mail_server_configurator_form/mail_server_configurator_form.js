/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";

/**
 * Allow to install the module before configuring the mail server
 * (if a module needs to be installed). We need JS code for it,
 * because we can not install the module and configure the mail server
 * in the same transaction (the python code needs to be re-loaded).
 */
export class MailServerConfiguratorController extends FormController {
    setup() {
        super.setup();
        this.action = useService("action");
    }

    async beforeExecuteActionButton(clickParams) {
        await super.beforeExecuteActionButton(...arguments);
        if (clickParams.name == "action_setup" && this.model.root.data.need_module_install) {
            // after installing the module, configure the mail server
            // this can not be done in the same transaction, because
            // the python code need to be re-loaded after the module
            // has been installed
            await this.action.doActionButton({
                type: "object",
                resId: this.model.root.resId,
                name: "action_install",
                resModel: "mail.server.configurator",
            });
        }
        return true;
    }
}

export const MailServerConfiguratorFormView = {
    ...formView,
    Controller: MailServerConfiguratorController,
};

registry.category("views").add("mail_server_configurator_form", MailServerConfiguratorFormView);
