import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

class RevealLinkBase extends Interaction {
    getDecodedHref() {
        const hrefB64 = this.el.getAttribute("hideref");
        return hrefB64 ? atob(hrefB64) : null;
    }

    revealHref() {
        const href = this.getDecodedHref();
        if (href) {
            this.el.setAttribute("href", href);
        }
    }
}

export class RevealLinkClick extends RevealLinkBase {
    static selector = "a[data-reveal-me='click']";

    dynamicContent = {
        _root: {
            "t-on-click": this.revealHref,
        },
    };
}

export class RevealLinkLoad extends RevealLinkBase {
    static selector = "a[data-reveal-me='load']";

    dynamicContent = {
        _root: {
            "t-att-href": () => this.getDecodedHref() || "#",
        },
    };
}

export class RevealLinkHover extends RevealLinkBase {
    static selector = "a[data-reveal-me='hover']";

    dynamicContent = {
        _root: {
            "t-on-mouseenter": this.revealHref,
        },
    };
}

registry.category("public.interactions").add("website.reveal_link_click", RevealLinkClick);
registry.category("public.interactions").add("website.reveal_link_load", RevealLinkLoad);
registry.category("public.interactions").add("website.reveal_link_hover", RevealLinkHover);
