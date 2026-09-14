/** @odoo-module native */
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { useEffect, useRef } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { patch } from "@web/core/utils/patch";

const log = makeLogger("portal.chatter.position");

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.topRef = useRef("top");
        useEffect(
            (topEl) => {
                if (!topEl) {
                    return;
                }
                const headerEl = document.querySelector("#wrapwrap header");
                if (
                    this.props.twoColumns ||
                    !headerEl ||
                    headerEl.matches(".o_header_sidebar")
                ) {
                    return;
                }
                const originalPadding = topEl.style.getPropertyValue("padding-top");
                const originalPriority = topEl.style.getPropertyPriority("padding-top");
                let appliedPadding;
                const updatePadding = () => {
                    const sticky = topEl.getBoundingClientRect().top < 1;
                    appliedPadding = sticky
                        ? `${headerEl.getBoundingClientRect().height + 15}px`
                        : "20px";
                    topEl.style.paddingTop = appliedPadding;
                    log.logic("update header offset", () => ({
                        sticky,
                        padding: appliedPadding,
                    }));
                };
                const observer = new IntersectionObserver(updatePadding, {
                    threshold: [1],
                });
                const resizeObserver = new ResizeObserver(updatePadding);
                observer.observe(topEl);
                resizeObserver.observe(headerEl);
                return () => {
                    observer.disconnect();
                    resizeObserver.disconnect();
                    // Do not overwrite a style that Owl or another owner replaced.
                    if (
                        topEl.style.paddingTop === appliedPadding &&
                        !topEl.style.getPropertyPriority("padding-top")
                    ) {
                        topEl.style.setProperty(
                            "padding-top",
                            originalPadding,
                            originalPriority,
                        );
                    }
                    log.lifecycle("header offset observers disconnected");
                };
            },
            () => [this.topRef.el, this.props.twoColumns],
        );
    },
});
