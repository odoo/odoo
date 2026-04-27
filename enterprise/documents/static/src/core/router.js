import { router } from "@web/core/browser/router";
import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";

/*
This prevents the router from trying to extract an action from the url if it starts with /odoo/documents
 */
browser.addEventListener(
    "click",
    (ev) => {
        if (ev.defaultPrevented || ev.target.closest("[contenteditable]")) {
            return;
        }
        const href = ev.target.closest("a")?.getAttribute("href");
        if (href && !href.startsWith("#")) {
            let url;
            try {
                // ev.target.href is the full url including current path
                url = new URL(href);
            } catch {
                return;
            }
            if (
                browser.location.host === url.host &&
                browser.location.pathname.startsWith("/odoo") &&
                url.pathname.startsWith("/odoo/documents/") &&
                ev.target.target !== "_blank"
            ) {
                ev.stopPropagation();
            }
        }
    },
    {
        capture: true,
    }
);

/* if you guys at framework-js read this, we are sorry, bigram-request */
patch(router, {
    stateToUrl(state) {
        const url = super.stateToUrl(state);
        if (url.startsWith("/odoo/documents") && state.access_token) {
            return (
                `/odoo/documents/${encodeURIComponent(state.access_token)}` +
                (Object.hasOwn(state, "debug") ? `?debug=${state.debug}` : "")
            );
        }
        return url;
    },
});
