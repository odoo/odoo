import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { session } from "@web/session";
import { Component } from "@odoo/owl";
import { isHTTPSorNakedDomainRedirection } from "./utils";

export class WebsiteSwitcherSystrayItem extends Component {
    static template = "website.WebsiteSwitcherSystrayItem";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {};
    setup() {
        this.websiteService = useService("website");
        this.notificationService = useService("notification");
        this.actionService = useService("action");
    }

    getElements() {
        return this.websiteService.websites.map((website) => ({
            name: website.name,
            id: website.id,
            domain: website.domain,
            dataset: Object.assign(
                {
                    "data-website-id": website.id,
                },
                website.domain
                    ? {}
                    : {
                          "data-tooltip": _t("This website does not have a domain configured."),
                          "data-tooltip-position": "left",
                      }
            ),
            callback: () => {
                if (
                    !session.website_bypass_domain_redirect && // Used by the Odoo support (bugs to be expected)
                    website.domain &&
                    !isHTTPSorNakedDomainRedirection(website.domain, window.location.origin)
                ) {
                    const {
                        location: { pathname, search, hash },
                    } = this.websiteService.contentWindow;
                    const path = pathname + search + hash;
                    // Automatically converts Unicode domains (e.g. düsseldorf.com) to
                    // punycode (ASCII-safe) using the native URL API
                    const url = new URL("/web", website.domain);
                    url.hash = new URLSearchParams({
                        action: "website.website_preview",
                        path: path,
                        website_id: website.id,
                    });
                    window.location.href = url;
                } else {
                    this.websiteService.goToWebsite({
                        websiteId: website.id,
                        path: "",
                        lang: "default",
                    });
                    if (!website.domain) {
                        const closeFn = this.notificationService.add(
                            _t("Add a domain to your website."),
                            {
                                type: "warning",
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
                                        name: "Settings",
                                    },
                                ],
                            }
                        );
                        browser.setTimeout(closeFn, 7000);
                    }
                }
            },
            class:
                website.id === this.websiteService.currentWebsite.id
                    ? "text-truncate active"
                    : "text-truncate",
        }));
    }
}
