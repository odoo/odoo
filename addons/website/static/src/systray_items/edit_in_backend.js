/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component, useEffect } = owl;

export class EditInBackendSystray extends Component {
    setup() {
        this.websiteService = useService('website');
        this.actionService = useService('action');

        useEffect(() => {
            this.websiteService.editedObjectPath = null;
        }, () => []);
    }

    getElements() {
        return [{
            title: this.env._t("Edit in backend"),
            callback: () => this.editInBackend(),
        }];
    }

    editInBackend() {
        const { metadata: { mainObject } } = this.websiteService.currentWebsite;
        this.websiteService.editedObjectPath = this.websiteService.contentWindow.location.pathname;
        this.actionService.doAction({
            res_model: mainObject.model,
            res_id: mainObject.id,
            views: [[false, "form"]],
            type: "ir.actions.act_window",
            view_mode: "form",
        });
    }
}
EditInBackendSystray.template = "website.EditInBackendSystray";
EditInBackendSystray.components = {
    Dropdown,
    DropdownItem
};

export const systrayItem = {
    Component: EditInBackendSystray,
    isDisplayed: env => env.services.website.currentWebsite && env.services.website.currentWebsite.metadata.editableInBackend,
};

registry.category("website_systray").add("EditInBackend", systrayItem, { sequence: 7 });
