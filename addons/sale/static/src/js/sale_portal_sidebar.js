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
        const payNowButton = this.el.querySelector('#o_sale_portal_paynow')
        if (searchParams.get("allow_payment") === "yes" && payNowButton) {
            payNowButton.click();
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
    _setElementId: function (prefix, el) {
        var id = uniqueId(prefix);
        this.spyWatched.querySelector(el).setAttribute('id', id);
        return id;
    },
    /**
     * generate the new spy menu
     *
     * @private
     *
     */
    _generateMenu: function () {
        var self = this,
            lastLI = false,
            lastUL = null,
            bsSidenav = this.el.querySelector('.bs-sidenav');

        Array.from(this.spyWatched.querySelectorAll("#quote_content [id^=quote_header_], #quote_content [id^=quote_]")).forEach(el => el.removeAttribute("id"));
        Array.from(this.spyWatched.querySelectorAll("#quote_content h2, #quote_content h3")).forEach((el) => {
            var id, text;
            switch (el.tagName.toLowerCase()) {
                case "h2":
                    id = self._setElementId('quote_header_', el);
                    text = self._extractText(el);
                    if (!text) {
                        break;
                    }
                    lastLI = document.createElement('li');
                    lastLI.className = 'nav-item';
                    lastLI.innerHTML = `<a class="nav-link p-0" href="#${id}">${text}</a>`;
                    bsSidenav.appendChild(lastLI);
                    lastUL = false;
                    break;
                case "h3":
                    id = self._setElementId('quote_', el);
                    text = self._extractText(el);
                    if (!text) {
                        break;
                    }
                    if (lastLI) {
                        if (!lastUL) {
                            lastUL = document.createElement('ul');
                            lastUL.className = 'nav flex-column';
                            lastLI.appendChild(lastUL);
                        }
                        let li = document.createElement('li');
                        li.className = 'nav-item';
                        li.innerHTML = `<a class="nav-link p-0" href="#${id}">${text}</a>`;
                        lastUL.appendChild(li);
                    }
                    break;
            }
            el.setAttribute('data-anchor', true);
        });
        this.trigger_up('widgets_start_request', {target: bsSidenav});
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
            var current = el;
            if (current.textContent.trim()) {
                var tagName = current.tagName;
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
