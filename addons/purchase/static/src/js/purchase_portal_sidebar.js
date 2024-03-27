/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import PortalSidebar from "@portal/js/portal_sidebar";
import { uniqueId } from "@web/core/utils/functions";

publicWidget.registry.PurchasePortalSidebar = PortalSidebar.extend({
    selector: ".o_portal_purchase_sidebar",

    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.authorizedTextTag = ["em", "b", "i", "u"];
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
    _setElementId: function (prefix, $el) {
        var id = uniqueId(prefix);
        // TODO: MSH: Need to convert this code
        $(this.spyWatched).find($el).attr("id", id);
        return id;
    },
    /**
     * generate the new spy menu
     *
     * @private
     *
     */
    _generateMenu: function () {
        let self = this,
            lastLI = false,
            lastUL = null,
            bsSidenav = this.el.querySelector(".bs-sidenav");
        let anchor;

        const quotes = document.querySelectorAll("#quote_content [id^=quote_header_], #quote_content [id^=quote_]") || this.spyWatched;
        quotes.forEach(quote => quote.attr("id", ""));
        const h2AndH3 = this.spyWatched.querySelectorAll("#quote_content h2, #quote_content h3");
        h2AndH3.forEach((el) => {
            var id, text;
            switch (el.tagName.toLowerCase()) {
                case "h2":
                    id = self._setElementId("quote_header_", el);
                    text = self._extractText(el);
                    if (!text) {
                        break;
                    }
                    lastLI = document.createElement('li');
                    lastLI.setAttribute('class', 'nav-item');
                    anchor = document.createElement('a');
                    anchor.setAttribute('class', 'nav-link p-0');
                    anchor.setAttribute('style', 'max-width: 200px;');
                    anchor.setAttribute('href', `"#${id}"`);
                    anchor.textContent = text;
                    lastLI.appendChild(anchor);
                    bsSidenav.appendChild(lastLI);
                    lastUL = false;
                    break;
                case "h3":
                    id = self._setElementId("quote_", el);
                    text = self._extractText(el);
                    if (!text) {
                        break;
                    }
                    if (lastLI) {
                        if (!lastUL) {
                            lastUL = document.createElement('ul');
                            lastUL.setAttribute('class', 'nav flex-column');
                            lastLI.appendChild(lastUL);
                        }
                        const li = document.createElement('li');
                        li.setAttribute('class', 'nav-item');
                        anchor = document.createElement('a');
                        anchor.setAttribute('class', 'nav-link p-0');
                        anchor.setAttribute('style', 'max-width: 200px;');
                        anchor.setAttribute('href', `"#${id}"`);
                        anchor.textContent = text;
                        li.appendChild(anchor);
                        lastUL.appendChild(li);
                    }
                    break;
            }
            el.setAttribute("data-anchor", true);
        });
        // TODO: MSH: Need to convert widgets_start_request first to convert following code
        this.trigger_up("widgets_start_request", { $target: $(bsSidenav) });
    },
    /**
     * extract text of menu title for sidebar
     *
     * @private
     * @param {Object} $node
     *
     */
    _extractText: function (node) {
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
});
