/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

const { Component } = owl;

class WebsiteSwitcherSystray extends Component {
    setup() {
        this.websiteService = useService('website');
    }

    getElements() {
        return this.websiteService.websites.map(({name, id}) => ({
            name,
            callback: () => this.websiteService.goToWebsite({ websiteId: id }),
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
