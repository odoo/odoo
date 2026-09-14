/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { deserializeDate } from "@web/core/l10n/dates";
import { luxon } from "@web/core/l10n/luxon";
import { _t } from "@web/core/translation";
import { uniqueId } from "@web/core/utils/functions";
import { Interaction } from "@web/public/interaction";

const { DateTime } = luxon;
const log = makeLogger("portal.sidebar");

export class Sidebar extends Interaction {
    setup() {
        this.printContent = undefined;
        this.spyWatched = undefined;
        this.menuItems = [];
        this.registerCleanup(() => this.clearMenu());
        this.authorizedTextTag = ["em", "strong", "b", "i", "u"];
    }

    start() {
        this.setDelayLabel();
    }

    setDelayLabel() {
        const timeagoEls = this.el.querySelectorAll(".o_portal_sidebar_timeago");
        const today = DateTime.now().startOf("day");
        for (const timeagoEl of timeagoEls) {
            const raw = timeagoEl.getAttribute("datetime");
            if (!raw) {
                continue;
            }
            const dateTime = deserializeDate(raw).startOf("day");
            if (!dateTime.isValid) {
                continue;
            }
            const diff = dateTime.diff(today, "days").days;
            if (diff === 0) {
                timeagoEl.innerText = _t("Due today");
            } else if (diff > 0) {
                timeagoEl.innerText = _t("Due in %s days", Math.abs(diff).toFixed());
            } else {
                timeagoEl.innerText = _t("%s days overdue", Math.abs(diff).toFixed());
            }
        }
    }

    /**
     * @param {string} href
     */
    printIframeContent(href) {
        if (!this.printContent || this.printContent.getAttribute("src") !== href) {
            this.printContent?.remove();
            const iframeEl = document.createElement("iframe");
            iframeEl.setAttribute("id", "print_iframe_content");
            iframeEl.setAttribute("src", href);
            iframeEl.style.display = "none";
            this.printContent = iframeEl;
            this.printContentReady = false;
            this.addListener(iframeEl, "load", () => {
                if (this.printContent !== iframeEl) {
                    return;
                }
                this.printContentReady = true;
                log.logic("print loaded document");
                iframeEl.contentWindow.print();
            });
            this.insert(iframeEl, this.el);
        } else if (this.printContentReady) {
            this.printContent.contentWindow.print();
        }
    }

    /**
     * @param {string} prefix
     * @param {HTMLElement} el
     */
    ensureElementId(prefix, el) {
        if (el.id) {
            return el.id;
        }
        const id = uniqueId(prefix);
        const previousId = el.getAttribute("id");
        el.id = id;
        this.registerCleanup(() => {
            if (el.id === id) {
                if (previousId === null) {
                    el.removeAttribute("id");
                } else {
                    el.id = previousId;
                }
            }
        });
        return id;
    }

    clearMenu() {
        for (const item of this.menuItems) {
            this.services["public.interactions"].stopInteractions(item);
            item.remove();
        }
        this.menuItems = [];
    }

    generateMenu(linkStyle = {}) {
        this.clearMenu();
        const sidenav = this.el.querySelector(".bs-sidenav");
        if (!sidenav || !this.spyWatched) {
            return;
        }
        let section;
        let sublist;
        const headings = this.spyWatched.querySelectorAll(
            "#quote_content h2, #quote_content h3",
        );
        for (const heading of headings) {
            const isSection = heading.tagName === "H2";
            const text = this.extractText(heading);
            if (!text) {
                continue;
            }
            const id = this.ensureElementId(
                isSection ? "quote_header_" : "quote_",
                heading,
            );
            if (!heading.hasAttribute("data-anchor")) {
                heading.setAttribute("data-anchor", "true");
                this.registerCleanup(() => {
                    if (heading.getAttribute("data-anchor") === "true") {
                        heading.removeAttribute("data-anchor");
                    }
                });
            }
            const link = document.createElement("a");
            link.classList.add("nav-link", "p-0");
            link.href = `#${id}`;
            link.textContent = text;
            Object.assign(link.style, linkStyle);
            const item = document.createElement("li");
            item.classList.add("nav-item");
            item.appendChild(link);
            if (isSection || !section) {
                this.menuItems.push(item);
                if (isSection) {
                    section = item;
                    sublist = undefined;
                }
            } else {
                if (!sublist) {
                    sublist = document.createElement("ul");
                    sublist.classList.add("nav", "flex-column");
                    section.appendChild(sublist);
                }
                sublist.appendChild(item);
            }
        }
        for (const item of this.menuItems) {
            this.insert(item, sidenav, "beforeend", false);
        }
        log.logic("menu generated", () => ({ topLevelItems: this.menuItems.length }));
    }

    /**
     * @param {HTMLElement} quoteHeaderEl
     */
    extractText(quoteHeaderEl) {
        const rawText = [];
        for (const el of quoteHeaderEl.childNodes) {
            const tagName = el.tagName;
            const text = el.textContent.trim();
            if (
                text &&
                (el.nodeType === Node.TEXT_NODE ||
                    (tagName && this.authorizedTextTag.includes(tagName.toLowerCase())))
            ) {
                rawText.push(text);
            }
        }
        return rawText.join(" ");
    }
}
