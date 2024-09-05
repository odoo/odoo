/** @odoo-module **/

import { scrollTo } from "@web/core/utils/scrolling";
import publicWidget from "@web/legacy/js/public/public_widget";
import PortalSidebar from "@portal/js/portal_sidebar";
import { setHeight } from "@web/core/utils/misc"

publicWidget.registry.AccountPortalSidebar = PortalSidebar.extend({
    selector: '.o_portal_invoice_sidebar',

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        const invoiceHtmlEl = this.el.querySelector("iframe#invoice_html");
        const updateIframeSize = this._updateIframeSize.bind(this, invoiceHtmlEl);

        window.addEventListener("resize", updateIframeSize);

        const iframeDoc = invoiceHtmlEl.contentDocument || invoiceHtmlEl.contentWindow.document;
        if (iframeDoc.readyState === "complete") {
            updateIframeSize();
        } else {
            invoiceHtmlEl.addEventListener("load", updateIframeSize);
        }

        return def;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the iframe is loaded or the window is resized on customer portal.
     * The goal is to expand the iframe height to display the full report without scrollbar.
     *
     * @private
     * @param {object} $el: the iframe
     */
    _updateIframeSize(el) {
        const wrapwrapEl = el.contentDocument.querySelector("div#wrapwrap");

        // Set it to 0 first to handle the case where scrollHeight is too big for its content.
        setHeight(el, 0);
        setHeight(el, wrapwrapEl.scrollHeight);

        // scroll to the right place after iframe resize
        const isAnchor = /^#[\w-]+$/.test(window.location.hash)
        if (!isAnchor) {
            return;
        }
        const target = window.location.hash;
        if (!target.length) {
            return;
        }
        scrollTo(target, { behavior: "instant" });
    },
});
