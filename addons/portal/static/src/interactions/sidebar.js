import { Interaction } from "@web/public/interaction";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { uniqueId } from "@web/core/utils/functions";

const { DateTime } = luxon;

export class Sidebar extends Interaction {

    setup() {
        this.printContent = undefined;
        this.spyWatched = undefined;
        this.authorizedTextTag = ["em", "b", "i", "u"];
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
     * Create a unique id and added as a attribute of spyWatched element
     *
     * @param {string} prefix
     * @param {HTMLElement} el
     */
    setElementId(prefix, el) {
        const id = uniqueId(prefix);
        el.setAttribute("id", id);
        return id;
    }

    generateMenu(linkStyle = {}) {
        let lastLI = false;
        let lastUL = null;
        const bsSidenavEl = this.el.querySelector(".bs-sidenav");

        const quoteEls = document.querySelectorAll("#quote_content [id^=quote_header_], #quote_content [id^=quote_]");
        for (const quoteEl of quoteEls) {
            quoteEl.removeAttribute("id");
        }
        this.spyWatched.removeAttribute("id");

        const quoteHeaderEls = this.spyWatched.querySelectorAll("#quote_content h2, #quote_content h3");
        for (const quoteHeaderEl of quoteHeaderEls) {
            let id = null;
            let text = null;
            switch (quoteHeaderEl.tagName.toLowerCase()) {
                case "h2": {
                    id = this.setElementId("quote_header_", quoteHeaderEl);
                    text = this.extractText(quoteHeaderEl);
                    if (!text) {
                        break;
                    }
                    const linkEl = document.createElement("a");
                    linkEl.classList.add("nav-link", "p-0");
                    linkEl.href = `#${id}`;
                    linkEl.style = Object.assign(linkEl.style, linkStyle);
                    linkEl.innerText = text;

                    const liEl = document.createElement("li");
                    liEl.classList.add("nav-item");

                    liEl.appendChild(linkEl);
                    this.insert(liEl, bsSidenavEl);

                    lastLI = liEl;
                    lastUL = false;
                    break;
                }
                case "h3": {
                    id = this.setElementId("quote_", quoteHeaderEl);
                    text = this.extractText(quoteHeaderEl);
                    if (!text) {
                        break;
                    }
                    if (lastLI) {
                        if (!lastUL) {
                            const ulEl = document.createElement("ul");
                            ulEl.classList.add("nav", "flex-column");

                            this.insert(ulEl, lastLI);

                            lastUL = ulEl;
                        }
                        const linkEl = document.createElement("a");
                        linkEl.classList.add("nav-link", "p-0");
                        linkEl.href = `#${id}`;
                        linkEl.style = Object.assign(linkEl.style, linkStyle);
                        linkEl.innerText = text;

                        const liEl = document.createElement("li");
                        liEl.classList.add("nav-item");

                        liEl.appendChild(linkEl);
                        this.insert(liEl, lastUL);
                    }
                    break;
                }
            }
            quoteHeaderEl.setAttribute("data-anchor", true);
        }
    }

    /**
     * @param {HTMLElement} quoteHeaderEl
     */
    extractText(quoteHeaderEl) {
        const rawText = [];
        for (const el of quoteHeaderEl.childNodes) {
            const tagName = el.tagName;
            const text = el.textContent.trim();
            if (text && (!tagName || this.authorizedTextTag.includes(tagName.toLowerCase()))) {
                rawText.push(text);
            }
        }
        return rawText.join(" ");
    }
}
