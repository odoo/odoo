/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";

const { useSubEnv } = owl;

export class PortalWizardUserListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.isPortalActionOngoing = false;
        const defaultOnClickViewButton = this.env.onClickViewButton;
        useSubEnv({
            onClickViewButton: async (params) => {
                if (params.clickParams.name === 'action_refresh_modal' || this.isPortalActionOngoing) {
                    return false;
                }
                this.isPortalActionOngoing = true;
                await defaultOnClickViewButton(params);
                this.isPortalActionOngoing = false;
            },
        });
    }
}
