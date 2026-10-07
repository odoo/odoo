import { Sidebar } from "@portal/interactions/sidebar";
import { registry } from "@web/core/registry";

import { scrollTo } from "@web/core/utils/scrolling";

// Same page size as the document layout preview (iframe_wrapper_field.scss).
const PAGE_WIDTH = 1040;
const PAGE_HEIGHT = 1464;

export class AccountSidebar extends Sidebar {
    static selector = ".o_portal_invoice_sidebar";
    dynamicContent = {
        _window: { "t-on-resize": this.updateIframeSize },
        ".o_portal_invoice_print": { "t-on-click.prevent": this.onInvoicePrintClick },
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
            this.onIframeLoad();
        } else {
            this.addListener(this.invoiceHTMLEl, "load", this.onIframeLoad);
        }
    }

    onIframeLoad() {
        // Pin the footer to the bottom of the page.
        this.invoiceHTMLEl.contentDocument.querySelector("main").classList.add("d-flex", "flex-column", "min-vh-100");
        this.updateIframeSize();
    }

    /**
     * Called when the iframe is loaded or the window is resized on customer portal.
     * The goal is to display the full report as a page fitting the portal width, without scrollbar.
     */
    updateIframeSize() {
        const wrapwrapEl = this.invoiceHTMLEl.contentDocument.querySelector("div#wrapwrap");
        this.invoiceHTMLEl.width = PAGE_WIDTH;
        // Set it to 0 first to handle the case where scrollHeight is too big for its content.
        this.invoiceHTMLEl.height = 0;
        const height = Math.max(wrapwrapEl.scrollHeight, PAGE_HEIGHT);
        const scale = this.invoiceHTMLEl.parentElement.clientWidth / PAGE_WIDTH;
        this.invoiceHTMLEl.height = height;
        this.invoiceHTMLEl.style.transform = `scale(${scale})`;
        this.invoiceHTMLEl.parentElement.style.height = `${height * scale}px`;
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
     */
    onInvoicePrintClick(ev) {
        this.printIframeContent(ev.currentTarget.getAttribute("href"));
    }
}

registry
    .category("public.interactions")
    .add("account.account_sidebar", AccountSidebar);
