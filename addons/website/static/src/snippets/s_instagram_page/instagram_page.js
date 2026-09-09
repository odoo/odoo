/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { Interaction } from "@web/public/interaction";

const log = makeLogger("website.snippet.s_instagram_page");

export class InstagramPage extends Interaction {
    static selector = ".s_instagram_page";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _iframe: () => this.iframeEl,
    };
    dynamicContent = {
        _window: { "t-on-message": this.onMessage },
        _iframe: { "t-att-height": () => this.height },
    };

    setup() {
        this.iframeEl = document.createElement("iframe");
        this.iframeEl.setAttribute("scrolling", "no");
        this.iframeEl.setAttribute("aria-label", _t("Instagram"));
        this.iframeEl.classList.add("w-100");
        this.insert(this.iframeEl, this.el.querySelector(".o_instagram_container"));

        const iframeWidth = parseInt(getComputedStyle(this.iframeEl).width);
        this.height = Math.ceil(0.659 * iframeWidth + (iframeWidth < 432 ? 156 : 203));
        log.lifecycle("setup: iframe inserted", () => ({
            iframeWidth,
            height: this.height,
        }));
    }

    start() {
        const src = `https://www.instagram.com/${this.el.dataset.instagramPage}/embed`;
        log.lifecycle("start: src handed to cookie consent", () => ({
            page: this.el.dataset.instagramPage,
        }));
        this.services.website_cookies.manageIframeSrc(this.iframeEl, src);
    }

    /**
     * @param {Event} ev
     */
    onMessage(ev) {
        if (
            ev.origin !== "https://www.instagram.com" ||
            this.iframeEl.contentWindow !== ev.source
        ) {
            return;
        }
        let evDataJSON;
        try {
            evDataJSON = JSON.parse(ev.data);
        } catch {
            return;
        }
        if (evDataJSON.type !== "MEASURE") {
            return;
        }
        const height = parseInt(evDataJSON.details.height);
        if (height) {
            log.logic("onMessage: MEASURE height applied", () => ({
                previous: this.height,
                height,
            }));
            this.height = height;
        }
    }
}

registry.category("public.interactions").add("website.instagram_page", InstagramPage);
