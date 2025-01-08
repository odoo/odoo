import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class CookiesWarning extends Interaction {
    static selector = ".o_no_optional_cookie";

    dynamicSelectors = {
        ...this.dynamicSelectors,
        "_iframe": () => this.iframeEl,
    };
    dynamicContent = {
        "_root": { "t-on-click": this.showCookiesBar },
        "_iframe": { "t-att-class": () => ({ "d-none": !!this.el.parentElement }) },
    };

    setup() {
        this.iframeEl = this.el.previousElementSibling;
    }

    start() {
        this.addListener(
            document,
            "optionalCookiesAccepted",
            this.removeOptionalCookiesWarning,
            { once: true }
        );
    }

    showCookiesBar() {
        this.services.website_cookies.bus.trigger("cookiesBar.show");
    }

    removeOptionalCookiesWarning() {
        this.el.remove();
    }
}

registry.category("public.interactions").add("website.cookies_warning", CookiesWarning);
