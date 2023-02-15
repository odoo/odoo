/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import wUtils from 'website.utils';

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
                if (website.domain && !wUtils.isHTTPSorNakedDomainRedirection(website.domain, window.location.origin)) {
                    const { location: { pathname, search, hash } } = this.websiteService.contentWindow;
                    const path = pathname + search + hash;
                    window.location.href = `${website.domain}/web#action=website.website_preview&path=${encodeURI(path)}&website_id=${website.id}`;
                } else {
                    this.websiteService.goToWebsite({ websiteId: website.id });
                }
            },
            class: website.id === this.websiteService.currentWebsite.id ? 'active' : '',
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
    isDisplayed: env => env.services.website.hasMultiWebsites,
};

registry.category("website_systray").add("WebsiteSwitcher", systrayItem, { sequence: 11 });
