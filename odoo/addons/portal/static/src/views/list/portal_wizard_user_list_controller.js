/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";

export class PortalWizardUserListController extends ListController {
    setup() {
        super.setup();
        this.isPortalActionOngoing = false;
    }

    /**
     * @override
     */
     async beforeExecuteActionButton(clickParams) {
        if (clickParams.name === 'action_refresh_modal' || this.isPortalActionOngoing) {
            return false;
        }
        this.isPortalActionOngoing = true;
        return super.beforeExecuteActionButton(clickParams);
    }
    
    /**
     * @override
     */
    async afterExecuteActionButton(clickParams) {
        this.isPortalActionOngoing = false;
    }
}
