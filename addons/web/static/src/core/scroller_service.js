/** @odoo-module **/

import { browser } from "./browser/browser";
import { registry } from "./registry";
import { scrollTo } from "./utils/scrolling";

export const scrollerService = {
    start(env) {
        /**
         * Listen to click event to allow having links with href towards an anchor.
         * Since odoo use hashtag to represent the current state of the view, we can't
         * easily distinguish between a link towards an anchor and a link towards
         * another view/state. If we want to navigate towards an anchor, we must not
         * change the hash of the url otherwise we will be redirected to the app switcher
         * instead To check if we have an anchor, first check if we have an href
         * attribute starting with #. Try to find a element in the DOM using JQuery
         * selector. If we have a match, it means that it is probably a link to an
         * anchor, so we jump to that anchor.
         *
         * @param {MouseEvent} ev
         */
        browser.addEventListener("click", (ev) => {
            const link = ev.target.closest("a");
            if (!link) {
                return;
            }
            const disableAnchor = link.attributes.getNamedItem("disable_anchor");
            if (disableAnchor && disableAnchor.value === "true") {
                return;
            }
            const href = link.attributes.getNamedItem("href");
            if (href) {
                if (href.value[0] === "#") {
                    if (href.value.length === 1) {
                        ev.preventDefault(); // single hash in href are just a way to activate A-tags node
                        return;
                    }
                    let matchingEl = null;
                    try {
                        matchingEl = document.querySelector(`.o_content #${href.value.substr(1)}`);
                    } catch (e) {
                        // Invalid selector: not an anchor anyway
                    }
                    const triggerEv = new CustomEvent("anchor-link-clicked", {
                        detail: {
                            element: matchingEl,
                            id: href.value,
                            originalEv: ev,
                        },
                    });
                    env.bus.trigger("SCROLLER:ANCHOR_LINK_CLICKED", triggerEv);
                    if (matchingEl && !triggerEv.defaultPrevented) {
                        ev.preventDefault();
                        scrollTo(matchingEl, { isAnchor: true });
                    }
                }
            }
        });
    },
};

registry.category("services").add("scroller", scrollerService);
