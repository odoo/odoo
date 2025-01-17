/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { session } from "@web/session";
import wUtils from '@website/js/utils';
import { Component } from "@odoo/owl";

export class WebsiteSwitcherSystray extends Component {
    static template = "website.WebsiteSwitcherSystray";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {};
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
            dataset: Object.assign({
                'data-website-id': website.id,
            }, website.domain ? {} : {
                'data-tooltip': _t('This website does not have a domain configured.'),
                'data-tooltip-position': 'left',
            }),
            callback: () => {
                // TODO share this condition with the website_preview somehow
                // -> we should probably show the redirection warning here too
                if (!session.website_bypass_domain_redirect // Used by the Odoo support (bugs to be expected)
                        && website.domain
                        && !wUtils.isHTTPSorNakedDomainRedirection(website.domain, window.location.origin)) {
                    const { location: { pathname, search, hash } } = this.websiteService.contentWindow;
                    const path = pathname + search + hash;
                    window.location.href = `${encodeURI(website.domain)}/odoo/action-website.website_preview?path=${encodeURIComponent(path)}&website_id=${encodeURIComponent(website.id)}`;
                } else {
                    this.websiteService.goToWebsite({ websiteId: website.id, path: "", lang: "default" });
                    if (!website.domain) {
                        const closeFn = this.notificationService.add(
                            _t(
                                "This website does not have a domain configured. To avoid unexpected behaviours during website edition, we recommend closing (or refreshing) other browser tabs.\nTo remove this message please set a domain in your website settings"
                            ),
                            {
                                type: "warning",
                                title: _t(
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

export const systrayItem = {
    Component: WebsiteSwitcherSystray,
    isDisplayed: env => env.services.website.hasMultiWebsites,
};

registry.category("website_systray").add("WebsiteSwitcher", systrayItem, { sequence: 12 });
