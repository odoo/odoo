/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const websiteSystrayRegistry = registry.category('website_systray');

export class EditInBackendSystray extends Component {
    static template = "website.EditInBackendSystray";
    static props = {};
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

export const systrayItem = {
    Component: EditInBackendSystray,
    isDisplayed: env => env.services.website.currentWebsite && env.services.website.currentWebsite.metadata.editableInBackend,
};

registry.category("website_systray").add("EditInBackend", systrayItem, { sequence: 10 });
