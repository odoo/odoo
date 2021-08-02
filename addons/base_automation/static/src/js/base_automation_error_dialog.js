/** @odoo-module */

import { ErrorDialog } from "@web/core/errors/error_dialogs";
import session from "web.session";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BaseAutomationErrorDialog extends ErrorDialog {
    setup() {
        super.setup(...arguments);
        const { id, name } = this.props.data.context.base_automation;
        this.actionId = id;
        this.actionName = name;
        this.isUserAdmin = useService("user").isAdmin;
        this.actionService = useService("action");
        this.orm = useService("orm");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * This method is called when the user clicks on the 'Disable action' button
     * displayed when a crash occurs in the evaluation of an automated action.
     * Then, we write `active` to `False` on the automated action to disable it.
     *
     * @private
     * @param {MouseEvent} ev
     */
    async disableAction(ev) {
        await this.orm.write("base.automation", [this.actionId], {
            active: false,
        });
        this.close();
    }
    /**
     * This method is called when the user clicks on the 'Edit action' button
     * displayed when a crash occurs in the evaluation of an automated action.
     * Then, we redirect the user to the automated action form.
     *
     * @private
     * @param {MouseEvent} ev
     */
    editAction(ev) {
        this.actionService.doAction({
            name: "Automated Actions",
            res_model: "base.automation",
            res_id: this.actionId,
            views: [[false, "form"]],
            type: "ir.actions.act_window",
            view_mode: "form",
        });
        this.close();
    }
}

BaseAutomationErrorDialog.bodyTemplate = "base_automation.ErrorDialogBody";

registry.category("error_dialogs").add("base_automation", BaseAutomationErrorDialog);
