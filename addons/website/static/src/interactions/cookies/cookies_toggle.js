import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class CookiesToggle extends Interaction {
    static selector = ".o_cookies_bar_toggle";
    dynamicContent = {
        _root: {
            "t-on-click.prevent": () =>
                this.services.website_cookies.bus.trigger("cookiesBar.toggle"),
        },
    };
}

registry.category("public.interactions").add("website.cookies_toggle", CookiesToggle);
