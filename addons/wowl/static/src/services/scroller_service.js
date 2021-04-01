/** @odoo-module **/

import { serviceRegistry } from "../webclient/service_registry";
import { setScrollPosition } from "../utils/scrolling";

export const scrollerService = {
  async deploy() {
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
    document.addEventListener("click", (ev) => {
      const target = ev.target;
      if (target.tagName.toUpperCase() !== "A") {
        return;
      }
      const disableAnchor = target.attributes.getNamedItem("disable_anchor");
      if (disableAnchor && disableAnchor.value === "true") {
        return;
      }
      const href = target.attributes.getNamedItem("href");
      if (href) {
        if (href.value[0] === "#") {
          if (href.value.length === 1) {
            return;
          }
          let matchingEl = null;
          try {
            matchingEl = document.querySelector(`.o_content #${href.value.substr(1)}`);
          } catch (e) {
            // Invalid selector: not an anchor anyway
          }
          if (matchingEl) {
            ev.preventDefault();
            const offset = matchingEl.getBoundingClientRect();
            setScrollPosition(offset);
          }
        }
      }
    });
  },
};

serviceRegistry.add("scroller", scrollerService);
