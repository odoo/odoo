import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class CookiesWarning extends Interaction {
    static selector = ".o_no_optional_cookie";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _iframe: () => this.el.previousElementSibling,
    };
    dynamicContent = {
        _root: { "t-on-click": () => this.services.website_cookies.bus.trigger("cookiesBar.show") },
        _iframe: {
            "t-att-class": () => ({
                "d-none": !!this.el.parentElement,
            }),
        },
        _document: {
            "t-on-optionalCookiesAccepted.once": () => this.el.remove(),
        },
    };
}

registry
    .category("public.interactions")
    .add("website.cookies_warning", CookiesWarning);
