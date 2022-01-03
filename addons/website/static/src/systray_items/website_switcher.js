/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component } = owl;

export class WebsiteSwitcherSystray extends Component {
    setup() {
        this.websiteService = useService('website');
    }

    getElements() {
        return this.websiteService.websites.map((website) => ({
            name: website.name,
            id: website.id,
            callback: () => {
                this.websiteService.goToWebsite({ websiteId: website.id });
            },
        }));
    }
}
WebsiteSwitcherSystray.template = "website.WebsiteSwitcherSystray";
WebsiteSwitcherSystray.components = {
    Dropdown,
    DropdownItem,
};

export const systrayItem = {
    Component: WebsiteSwitcherSystray,
};

registry.category("website_systray").add("WebsiteSwitcher", systrayItem, { sequence: 11 });
