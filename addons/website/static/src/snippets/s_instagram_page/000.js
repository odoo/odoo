/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { ObservingCookieWidgetMixin } from "@website/snippets/observing_cookie_mixin";

// Note that Instagram can automatically detect the language of the user and
// translate the embed.

const InstagramPage = publicWidget.Widget.extend(ObservingCookieWidgetMixin, {
    selector: ".s_instagram_page",
    disabledInEditableMode: false,

    /**
     * @override
     */
    start() {
        const iframeEl = document.createElement("iframe");
        this.el.querySelector(".o_instagram_container").appendChild(iframeEl);
        iframeEl.setAttribute("scrolling", "no");
        iframeEl.setAttribute("aria-label", _t("Instagram"));
        iframeEl.classList.add("w-100");
        // We can already estimate the height of the iframe.
        iframeEl.height = this._estimateIframeHeight();
        // We have to setup the message listener before setting the src, because
        // the iframe can send a message before this JS is fully loaded.
        this.__onMessage = this._onMessage.bind(this);
        window.addEventListener("message", this.__onMessage);

        // We set the src now, we are ready to receive the message.
        const src = `https://www.instagram.com/${this.el.dataset.instagramPage}/embed`;
        this._manageIframeSrc(this.el, src);

        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        const iframeEl = this.el.querySelector(".o_instagram_container iframe");
        if (iframeEl) {
            iframeEl.remove();
            window.removeEventListener("message", this.__onMessage);
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Gives an estimation of the height of the Instagram iframe.
     *
     * @private
     * @returns {number}
     */
    _estimateIframeHeight() {
        // In the meantime Instagram doesn't send us a message with the height,
        // we use a formula to estimate the height of the iframe (the formula
        // has been found with a linear regression).
        const iframeEl = this.el.querySelector(".o_instagram_container iframe");
        const iframeWidth = parseInt(getComputedStyle(iframeEl).width);
        // The profile picture is smaller when width < 432px.
        return 0.659 * iframeWidth + (iframeWidth < 432 ? 156 : 203);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a message is sent. Instagram sends us a message with the
     * height of the iframe.
     *
     * @private
     * @param {Event} ev
     */
    _onMessage(ev) {
        const iframeEl = this.el.querySelector(".o_instagram_container iframe");
        if (!iframeEl) {
            // TODO: fix this case. We should never end up here. It happens when
            // - Drop Instagram snippet
            // - Undo
            // - Drop a new Instagram snippet
            // => The listener of the first one is still active because the
            // public widget has not been destroyed.
            window.removeEventListener("message", this.__onMessage);
            return;
        }
        if (ev.origin !== "https://www.instagram.com" || iframeEl.contentWindow !== ev.source) {
            // It's not a message from Instagram or it's a message from another
            // Instagram iframe.
            return;
        }
        const evDataJSON = JSON.parse(ev.data);
        if (evDataJSON.type !== "MEASURE") {
            // It's not a measure message.
            return;
        }
        const height = parseInt(evDataJSON.details.height);
        // Here we get the exact height of the iframe.
        // Instagram can return a height of 0 before the real height.
        if (height) {
            // Prevent history step in edit mode.
            this.options.wysiwyg?.odooEditor.observerUnactive();
            iframeEl.height = height;
            this.options.wysiwyg?.odooEditor.observerActive();
        }
    },
});

publicWidget.registry.InstagramPage = InstagramPage;

export default InstagramPage;
