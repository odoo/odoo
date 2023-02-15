/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";

const { Component, onWillStart, useState } = owl;

const websiteSystrayRegistry = registry.category('website_systray');

export class EditInBackendSystray extends Component {
    setup() {
        this.websiteService = useService('website');
        this.actionService = useService('action');
        this.state = useState({mainObjectName: ''});

        onWillStart(this._updateMainObjectName);
        useBus(websiteSystrayRegistry, 'CONTENT-UPDATED', this._updateMainObjectName);
    }

    editInBackend() {
        const { metadata: { mainObject } } = this.websiteService.currentWebsite;
        this.actionService.doAction({
            res_model: mainObject.model,
            res_id: mainObject.id,
            views: [[false, "form"]],
            type: "ir.actions.act_window",
            view_mode: "form",
        });
    }

    async _updateMainObjectName() {
        this.state.mainObjectName = await this.websiteService.getUserModelName();
    }
}
EditInBackendSystray.template = "website.EditInBackendSystray";

export const systrayItem = {
    Component: EditInBackendSystray,
    isDisplayed: env => env.services.website.currentWebsite && env.services.website.currentWebsite.metadata.editableInBackend,
};

registry.category("website_systray").add("EditInBackend", systrayItem, { sequence: 9 });
