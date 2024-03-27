/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import PortalSidebar from "@portal/js/portal_sidebar";
import { uniqueId } from "@web/core/utils/functions";

publicWidget.registry.PurchasePortalSidebar = PortalSidebar.extend({
    selector: ".o_portal_purchase_sidebar",
    events: {
        "click .o_portal_decline": "_onDecline",
        "click .o_portal_accept": "_onAccept",
    },

    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.authorizedTextTag = ["em", "b", "i", "u"];
        this.spyWatched = document.querySelector('body[data-target=".navspy"]');
        this.orm = this.bindService("orm");
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
     * @param {Object} $el
     *
     */
    _setElementId(prefix, el) {
        var id = uniqueId(prefix);
        if (el) {
            [...this.spyWatched.querySelectorAll(el.tagName)]
                .find((newel) => newel === el)
                ?.setAttribute("id", id);
        }
        return id;
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
        let lastLIEl = false;
        let lastULEl = null;
        let anchorEl;

        const quoteELs =
            document.querySelectorAll(
                "#quote_content [id^=quote_header_], #quote_content [id^=quote_]"
            ) || this.spyWatched;
        quoteELs.forEach((quoteEl) => quoteEl.setAttribute("id", ""));
        this.spyWatched.querySelectorAll("#quote_content h2, #quote_content h3").forEach((el) => {
            var id, text;
            switch (el.tagName.toLowerCase()) {
                case "h2":
                    id = self._setElementId("quote_header_", el);
                    text = self._extractText(el);
                    if (!text) {
                        break;
                    }
                    lastLIEl = document.createElement("li");
                    lastLIEl.setAttribute("class", "nav-item");
                    anchorEl = document.createElement("a");
                    anchorEl.setAttribute("class", "nav-link p-0");
                    anchorEl.setAttribute("style", "max-width: 200px;");
                    anchorEl.setAttribute("href", `"#${id}"`);
                    anchorEl.textContent = text;
                    lastLIEl.appendChild(anchorEl);
                    bsSidenavEl?.appendChild(lastLIEl);
                    lastULEl = false;
                    break;
                case "h3":
                    id = self._setElementId("quote_", el);
                    text = self._extractText(el);
                    if (!text) {
                        break;
                    }
                    if (lastLIEl) {
                        if (!lastULEl) {
                            lastULEl = document.createElement("ul");
                            lastULEl.setAttribute("class", "nav flex-column");
                            lastLIEl.appendChild(lastULEl);
                        }
                        const liEl = document.createElement("li");
                        liEl.setAttribute("class", "nav-item");
                        anchorEl = document.createElement("a");
                        anchorEl.setAttribute("class", "nav-link p-0");
                        anchorEl.setAttribute("style", "max-width: 200px;");
                        anchorEl.setAttribute("href", `"#${id}"`);
                        anchorEl.textContent = text;
                        liEl.appendChild(anchorEl);
                        lastULEl.appendChild(liEl);
                    }
                    break;
            }
            el.setAttribute("data-anchor", true);
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
    _extractText(node) {
        var self = this;
        var rawText = [];
        Array.from(node.childNodes).forEach((el) => {
            if (el.textContent.trim()) {
                const tagName = el.tagName;
                if (
                    typeof tagName === "undefined" ||
                    (typeof tagName !== "undefined" &&
                        self.authorizedTextTag.includes(tagName.toLowerCase()))
                ) {
                    rawText.push(el.textContent.trim());
                }
            }
        });
        return rawText.join(" ");
    },
    _onDecline: function (ev) {
        const orderId = parseInt(ev.currentTarget.dataset.orderId);
        this.orm.call("purchase.order", "decline_reception_mail", [orderId]);
    },
    _onAccept: function (ev) {
        const orderId = parseInt(ev.currentTarget.dataset.orderId);
        this.orm.call("purchase.order", "confirm_reception_mail", [orderId]);
    },
});
