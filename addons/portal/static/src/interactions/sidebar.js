import { Interaction } from "@web/public/interaction";

import { _t } from "@web/core/l10n/translation";
import { deserializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export class Sidebar extends Interaction {

    setup() {
        this.printContent = undefined;
    }

    start() {
        this.setDelayLabel();
    }

    /**
     * Set the due/delay information according to the given date
     * like : <span class="o_portal_sidebar_timeago" t-att-datetime="invoice.date_due"/>
     */
    setDelayLabel() {
        const timeagoEls = this.el.querySelectorAll(".o_portal_sidebar_timeago");
        for (const timeagoEl of timeagoEls) {
            const dateTime = deserializeDateTime(timeagoEl.getAttribute("datetime")).startOf("day");
            const today = DateTime.now().startOf("day");
            const diff = dateTime.diff(today).as("days");
            if (diff === 0) {
                timeagoEl.innerText = _t('Due today');
            } else if (diff > 0) {
                timeagoEl.innerText = _t('Due in %s days', Math.abs(diff).toFixed());
            } else {
                timeagoEl.innerText = _t('%s days overdue', Math.abs(diff).toFixed());
            }
        }
    }

    /**
     * @param {string} href
     */
    printIframeContent(href) {
        if (!this.printContent) {
            const iframeEl = document.createElement("iframe");
            iframeEl.setAttribute("id", "print_iframe_content");
            iframeEl.setAttribute("href", href);
            iframeEl.style.display = "none";
            this.printContent = iframeEl;
            this.insert(this.printContent, this.el);
            this.addListener(this.printContent, "load", () => this.printContent.contentWindow.print());
        } else {
            this.printContent.contentWindow.print()
        }
    }

    /**
     * @param {HTMLElement} quoteHeaderEl
     */
    extractText(quoteHeaderEl) {
        const rawText = [];
        for (const el of quoteHeaderEl.childNodes) {
            const text = el.textContent.trim();
            const tagName = el.tagName?.toLowerCase();
            if (text && (!tagName || this.authorizedTextTag.includes(tagName))) {
                rawText.push(text);
            }
        }
        return rawText.join(" ");
    }
}
