import { Sidebar } from "@portal/interactions/sidebar";
import { registry } from "@web/core/registry";

import { scrollTo } from "@web/core/utils/scrolling";

export class AccountSidebar extends Sidebar {
    static selector = ".o_portal_invoice_sidebar";
    dynamicContent = {
        _window: { "t-on-resize": this.updateIframeSize },
        ".o_portal_invoice_print": { "t-on-click.prevent.withTarget": this.onInvoicePrintClick },
    };

    setup() {
        super.setup();
        this.invoiceHTMLEl = undefined;
    }

    start() {
        super.start();
        this.invoiceHTMLEl = document.getElementById('invoice_html');
        const iframeDoc = this.invoiceHTMLEl.contentDocument || this.invoiceHTMLEl.contentWindow.document;
        if (iframeDoc.readyState === 'complete') {
            this.updateIframeSize();
        } else {
            this.addListener(this.invoiceHTMLEl, "load", this.updateIframeSize);
        }
    }

    /**
     * Called when the iframe is loaded or the window is resized on customer portal.
     * The goal is to expand the iframe height to display the full report without scrollbar.
     */
    updateIframeSize() {
        const wrapwrapEl = this.invoiceHTMLEl.contentDocument.querySelector("div#wrapwrap");
        // Set it to 0 first to handle the case where scrollHeight is too big for its content.
        this.invoiceHTMLEl.height = 0;
        this.invoiceHTMLEl.height = wrapwrapEl.scrollHeight;
        // scroll to the right place after iframe resize
        const isAnchor = /^#[\w-]+$/.test(window.location.hash)
        if (!isAnchor) {
            return;
        }
        const targetEl = document.querySelector(`${window.location.hash}`);
        if (!targetEl) {
            return;
        }
        scrollTo(targetEl, { behavior: "instant" });
    }

    /**
     * @param {MouseEvent} ev
     * @param {HTMLElement} currentTargetEl
     */
    onInvoicePrintClick(ev, currentTargetEl) {
        this.printIframeContent(currentTargetEl.getAttribute("href"));
    }
}

registry
    .category("public.interactions")
    .add("account.account_sidebar", AccountSidebar);
