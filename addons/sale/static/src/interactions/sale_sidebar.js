import { Sidebar } from "@portal/interactions/sidebar";
import { registry } from "@web/core/registry";

import { uniqueId } from "@web/core/utils/functions";

export class SaleSidebar extends Sidebar {
    static selector = ".o_portal_sale_sidebar";

    setup() {
        super.setup();
        this.authorizedTextTag = ["em", "b", "i", "u"];
        this.spyWatched = document.querySelector("body[data-target='.navspy']");
    }

    start() {
        super.start();
        const spyWatcheElement = this.el.querySelector("[data-id='portal_sidebar']");
        this.setElementId("", spyWatcheElement);
        // Nav Menu ScrollSpy
        this.generateMenu();
        // After signature, automatically open the popup for payment
        const searchParams = new URLSearchParams(window.location.search.substring(1));
        if (searchParams.get("allow_payment") === "yes") {
            this.el.querySelector("#o_sale_portal_paynow")?.click();
        }
    }

    /**
     * create an unique id and added as a attribute of spyWatched element
     *
     * @param {string} prefix
     * @param {HTMLElement} el
     */
    setElementId(prefix, el) {
        const id = uniqueId(prefix);
        el?.setAttribute("id", id);
        return id;
    }

    generateMenu() {
        let lastLI = false;
        let lastUL = null;
        const bsSidenavEl = this.el.querySelector(".bs-sidenav");

        const quoteEls = document.querySelectorAll("#quote_content [id^=quote_header_], #quote_content [id^=quote_]");
        for (const quoteEl of quoteEls) {
            quoteEl.removeAttribute("id");
        };
        this.spyWatched.removeAttribute("id");

        const quoteHeaderEls = this.spyWatched.querySelectorAll("#quote_content h2, #quote_content h3");
        for (const quoteHeaderEl of quoteHeaderEls) {
            let id = null;
            let text = null;
            switch (quoteHeaderEl.tagName.toLowerCase()) {
                case "h2":
                    id = this.setElementId("quote_header_", quoteHeaderEl);
                    text = this.extractText(quoteHeaderEl);
                    if (!text) {
                        break;
                    }
                    const linkEl = document.createElement("a");
                    linkEl.classList.add("nav-link", "p-0");
                    linkEl.href = `#${id}`;
                    linkEl.innerText = text;

                    const liEl = document.createElement("li");
                    liEl.classList.add("nav-item");

                    liEl.appendChild(linkEl);
                    this.insert(liEl, bsSidenavEl);

                    lastLI = liEl;
                    lastUL = false;
                    break;
                case "h3":
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
                        linkEl.innerText = text;

                        const liEl = document.createElement("li");
                        liEl.classList.add("nav-item");

                        liEl.appendChild(linkEl);
                        this.insert(liEl, lastUL);
                    }
                    break;
            }
            quoteHeaderEl.setAttribute("data-anchor", true);
        }
    }
}

registry
    .category("public.interactions")
    .add("sale.sale_sidebar", SaleSidebar);
