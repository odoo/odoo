import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { PortalChatterPlugin } from "@portal/chatter/portal/portal_chatter_plugin";
import { maybePlugin } from "@mail/utils/common/misc";

import { patch } from "@web/core/utils/patch";
import { onWillPatch } from "@odoo/owl";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.portalChatterPlugin = maybePlugin(PortalChatterPlugin);
        this.topRef = useRef("top");
        onWillPatch(() => {
            // Keep the composer position under the page header on scrolling
            // unless the header is on the side.
            const headerEl = document.querySelector("#wrapwrap header");
            if (!this.twoColumns() && headerEl && !headerEl.matches(".o_header_sidebar")) {
                const paddingTop = headerEl.getBoundingClientRect().height + 15 + "px";
                this.observer = new window.IntersectionObserver(
                    ([e]) =>
                        (e.target.style.paddingTop =
                            e.target.getBoundingClientRect().y < 1 ? paddingTop : "20px"),
                    {
                        threshold: [1],
                    }
                );
            }
        });
        useLayoutEffect(
            () => {
                if (this.topRef.el) {
                    this.observer?.observe(this.topRef.el);
                }
            },
            () => [this.topRef.el]
        );
    },

    get extraMessageFetchRouteParams() {
        return super.extraMessageFetchRouteParams;
    },
});
