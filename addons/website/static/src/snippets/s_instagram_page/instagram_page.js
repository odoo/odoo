import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";

// Note that Instagram can automatically detect the language of the user and
// translate the embed.

export class InstagramPage extends Interaction {
    static selector = ".s_instagram_page";
    dynamicContent = {
        // We have to setup the message listener before setting the src, because
        // the iframe can send a message before this JS is fully loaded.
        _window: {
            "t-on-message": this.onMessage,
        },
    }

    setup() {
        this.iframeEl = document.createElement("iframe");
        this.iframeEl.setAttribute("scrolling", "no");
        this.iframeEl.setAttribute("aria-label", _t("Instagram"));
        this.iframeEl.classList.add("w-100");

        // In the meantime Instagram doesn't send us a message with the height,
        // we use a formula to estimate the height of the iframe (the formula
        // has been found with a linear regression).
        const iframeWidth = parseInt(getComputedStyle(this.iframeEl).width);
        // The profile picture is smaller when width < 432px.
        this.iframeEl.height = 0.659 * iframeWidth + (iframeWidth < 432 ? 156 : 203);

        // TODO : Check if the next lines can be replace by `this.insert(this.iframeEl, this.el.querySelector(".o_instagram_container"));`

        this.el.querySelector(".o_instagram_container").appendChild(this.iframeEl);
        // TODO : ...observerUnactive() / ...observerActive()
        this.registerCleanup(() => { this.iframeEl.remove(); });
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
        // TODO Check if this issue is fixed with the new editor
        /*
        if (!this.iframeEl) {
            // TODO: fix this case. We should never end up here. It happens when
            // - Drop Instagram snippet
            // - Undo
            // - Drop a new Instagram snippet
            // => The listener of the first one is still active because the
            // public widget has not been destroyed.
            window.removeEventListener("message", this.__onMessage);
            return;
        }
        */
        if (ev.origin !== "https://www.instagram.com" || this.iframeEl.contentWindow !== ev.source) {
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
            // this.options.wysiwyg?.odooEditor.observerUnactive();
            this.iframeEl.height = height;
            // this.options.wysiwyg?.odooEditor.observerActive();
        }
    }
}

registry
    .category("public.interactions")
    .add("website.instagram_page", InstagramPage);

registry
    .category("public.interactions.edit")
    .add("website.instagram_page", { Interaction: InstagramPage });
