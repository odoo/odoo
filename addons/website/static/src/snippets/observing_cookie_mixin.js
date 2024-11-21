export const ObservingCookieWidgetMixin = {
    /**
     * Updates the element's iframe according to whether the cookies should be
     * approved (marked by `_post_processing_att` server-side).
     *
     * @private
     * @param {HTMLElement} rootEl - root element of the widget.
     * @param {string} src - src to set on the iframe.
     */
    _manageIframeSrc(rootEl, src) {
        const iframeEl = rootEl.querySelector("iframe");
        if (!rootEl.dataset.needCookiesApproval) {
            iframeEl.setAttribute("src", src);
        } else {
            iframeEl.dataset.nocookieSrc = src;
            iframeEl.setAttribute("src", "about:blank");
            $(iframeEl).trigger("add_cookies_warning");
        }
    },
};
