import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";

// Note that Instagram can automatically detect the language of the user and
// translate the embed.

export class InstagramPage extends Interaction {
    static selector = ".s_instagram_page";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _iframe: () => this.iframeEl,
    };
    dynamicContent = {
        // We have to setup the message listener before setting the src, because
        // the iframe can send a message before this JS is fully loaded.
        _window: { "t-on-message": this.onMessage },
        _iframe: { "t-att-height": () => this.height },
    };

    setup() {
        this.iframeEl = document.createElement("iframe");
        this.iframeEl.setAttribute("scrolling", "no");
        this.iframeEl.setAttribute("aria-label", _t("Instagram"));
        this.iframeEl.classList.add("w-100");
        this.insert(this.iframeEl, this.el.querySelector(".o_instagram_container"));

        // In the meantime Instagram doesn't send us a message with the height,
        // we use a formula to estimate the height of the iframe (the formula
        // has been found with a linear regression).
        const iframeWidth = parseInt(getComputedStyle(this.iframeEl).width);
        // The profile picture is smaller when width < 432px.
        this.height = Math.ceil(0.659 * iframeWidth + (iframeWidth < 432 ? 156 : 203));
    }

    start() {
        const src = `https://www.instagram.com/${this.el.dataset.instagramPage}/embed`;
        this.services.website_cookies.manageIframeSrc(this.iframeEl, src);
    }

    /**
     * Instagram sends us a message with the height of the iframe.
     *
     * @param {Event} ev
     */
    onMessage(ev) {
        if (
            ev.origin !== "https://www.instagram.com" ||
            this.iframeEl.contentWindow !== ev.source
        ) {
            return;
        }
        const evDataJSON = JSON.parse(ev.data);
        if (evDataJSON.type !== "MEASURE") {
            return;
        }
        const height = parseInt(evDataJSON.details.height);
        // Here we get the exact height of the iframe.
        // Instagram can return a height of 0 before the real height.
        if (height) {
            this.height = height;
        }
    }
}

registry.category("public.interactions").add("website.instagram_page", InstagramPage);
