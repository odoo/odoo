/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import PortalSidebar from "@portal/js/portal_sidebar";
import { uniqueId } from "@web/core/utils/functions";

publicWidget.registry.SalePortalSidebar = PortalSidebar.extend({
    selector: '.o_portal_sale_sidebar',

    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.authorizedTextTag = ['em', 'b', 'i', 'u'];
        this.spyWatched = document.querySelector('body[data-target=".navspy"]');
    },
    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        const spyWatcheElement = this.el.querySelector('[data-id="portal_sidebar"]');
        this._setElementId(spyWatcheElement);
        // Nav Menu ScrollSpy
        this._generateMenu();
        // After signature, automatically open the popup for payment
        const searchParams = new URLSearchParams(window.location.search.substring(1));
        const payNowButtonEl = this.el.querySelector("#o_sale_portal_paynow");
        if (searchParams.get("allow_payment") === "yes" && payNowButtonEl) {
            payNowButtonEl.click();
        }
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //---------------------------------------------------------------------------

    /**
     * create an unique id and added as a attribute of spyWatched element
     *
     * @private
     * @param {string} prefix
     * @param {Object} el
     *
     */
    _setElementId(prefix, el) {
        if (el) {
            const id = uniqueId(prefix);
            [...this.spyWatched.querySelectorAll(el.tagName)]
                .find((newel) => newel === el)
                ?.setAttribute("id", id);
            return id;
        }
    },
    /**
     * generate the new spy menu
     *
     * @private
     *
     */
    _generateMenu: function () {
        const self = this,
            bsSidenavEl = this.el.querySelector(".bs-sidenav");
        let lastLIEl = false,
            lastULEl = null;

        Array.from(
            this.spyWatched.querySelectorAll(
                "#quote_content [id^=quote_header_], #quote_content [id^=quote_]"
            )
        ).forEach((el) => el.removeAttribute("id"));
        Array.from(
            this.spyWatched.querySelectorAll("#quote_content h2, #quote_content h3")
        ).forEach((el) => {
            var id, text;
            switch (el.tagName.toLowerCase()) {
                case "h2":
                    id = self._setElementId('quote_header_', el);
                    text = self._extractText(el);
                    if (!text) {
                        break;
                    }
                    lastLIEl = document.createElement("li");
                    lastLIEl.className = "nav-item";
                    lastLIEl.innerHTML = `<a class="nav-link p-0" href="#${id}">${text}</a>`;
                    bsSidenavEl?.appendChild(lastLIEl);
                    lastULEl = false;
                    break;
                case "h3":
                    id = self._setElementId('quote_', el);
                    text = self._extractText(el);
                    if (!text) {
                        break;
                    }
                    if (lastLIEl) {
                        if (!lastULEl) {
                            lastULEl = document.createElement("ul");
                            lastULEl.className = "nav flex-column";
                            lastLIEl.appendChild(lastULEl);
                        }
                        const liEl = document.createElement("li");
                        liEl.className = "nav-item";
                        liEl.innerHTML = `<a class="nav-link p-0" href="#${id}">${text}</a>`;
                        lastULEl.appendChild(liEl);
                    }
                    break;
            }
            el.setAttribute('data-anchor', true);
        });
        this.trigger_up("widgets_start_request", { target: bsSidenavEl });
    },
    /**
     * extract text of menu title for sidebar
     *
     * @private
     * @param {Object} node
     *
     */
    _extractText: function (node) {
        var self = this;
        var rawText = [];
        Array.from(node.childNodes).forEach((el) => {
            const current = el;
            if (current.textContent.trim()) {
                const tagName = current.tagName;
                if (
                    typeof tagName === "undefined" ||
                    (typeof tagName !== "undefined" &&
                        self.authorizedTextTag.includes(tagName.toLowerCase()))
                ) {
                    rawText.push(current.textContent.trim());
                }
            }
        });
        return rawText.join(' ');
    },
});
