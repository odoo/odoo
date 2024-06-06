/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import wUtils from 'website.utils';

const { Component } = owl;

export class WebsiteSwitcherSystray extends Component {
    setup() {
        this.websiteService = useService('website');
        this.notificationService = useService("notification");
        this.actionService = useService("action");
    }

    getElements() {
        return this.websiteService.websites.map((website) => ({
            name: website.name,
            id: website.id,
            domain: website.domain,
            callback: () => {
                if (website.domain && !wUtils.isHTTPSorNakedDomainRedirection(website.domain, window.location.origin)) {
                    const { location: { pathname, search, hash } } = this.websiteService.contentWindow;
                    const path = pathname + search + hash;
                    window.location.href = `${website.domain}/web#action=website.website_preview&path=${encodeURIComponent(path)}&website_id=${encodeURIComponent(website.id)}`;
                } else {
                    this.websiteService.goToWebsite({ websiteId: website.id });
                    if (!website.domain) {
                        const closeFn = this.notificationService.add(
                            this.env._t(
                                "This website does not have a domain configured. To avoid unexpected behaviours during website edition, we recommend closing (or refreshing) other browser tabs.\nTo remove this message please set a domain in your website settings"
                            ),
                            {
                                type: "warning",
                                title: this.env._t(
                                    "No website domain configured for this website."
                                ),
                                sticky: true,
                                buttons: [
                                    {
                                        onClick: () => {
                                            this.actionService.doAction(
                                                "website.action_website_configuration"
                                            );
                                            closeFn();
                                        },
                                        primary: true,
                                        name: "Go to Settings",
                                    },
                                ],
                            }
                        );
                        browser.setTimeout(closeFn, 7000);
                    }
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
