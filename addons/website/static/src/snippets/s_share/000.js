import publicWidget from '@web/legacy/js/public/public_widget';

const ShareWidget = publicWidget.Widget.extend({
    selector: '.s_share, .oe_share', // oe_share for compatibility
    events: {
        'click a': '_onShareLinkClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Everything is done on click here (even changing the href) as the URL we
     * want to share may be updated during the page use (like when updating
     * variant on a product page then clicking on a share link).
     *
     * @private
     */
    _onShareLinkClick(ev) {
        const urlParams = ["u", "url", "body"];
        const titleParams = ["title", "text", "subject", "description"];
        const mediaParams = ["media"];
        const aEl = ev.currentTarget;
        // We don't modify the original URL in case the user clicks again on the
        // sharer later.
        const modifiedUrl = new URL(aEl.href);

        // Try and support old use of share snippet as a social link snippet:
        // if the URL does not look like a sharer, then do nothing. This
        // obviously won't cover all cases (people may have added URL that look
        // like sharer but are not but in that case, it was probably already
        // broken before).
        if (![...urlParams, ...titleParams, ...mediaParams]
                .some(param => modifiedUrl.searchParams.has(param))) {
            return;
        }

        ev.preventDefault();
        ev.stopPropagation();

        // We don't need to encode the URL as searchParams.set does it for us.
        const currentUrl = window.location.href;

        const urlParamFound = urlParams.find(param => modifiedUrl.searchParams.has(param));
        if (urlParamFound) {
            modifiedUrl.searchParams.set(urlParamFound, currentUrl);
        }

        const titleParamFound = titleParams.find(param => modifiedUrl.searchParams.has(param));
        if (titleParamFound) {
            // We don't need to encode the title as searchParams.set does it.
            const currentTitle = document.title;
            if (aEl.classList.contains('s_share_whatsapp')) {
                // WhatsApp does not support the "url" GET parameter.
                // Instead we need to include the url within the passed "text"
                // parameter, merging everything together, e.g of output:
                // https://wa.me/?text=%20OpenWood%20Collection%20Online%20Reveal%20%7C%20My%20Website%20http%3A%2F%2Flocalhost%3A8888%2Fevent%2Fopenwood-collection-online-reveal-2021-06-21-2021-06-23-8%2Fregister
                // For more details, see https://faq.whatsapp.com/general/chats/how-to-use-click-to-chat/
                modifiedUrl.searchParams.set(titleParamFound, `${currentTitle} ${currentUrl}`);
            } else {
                // The built-in `URLSearchParams.set()` method encodes spaces
                // as "+" characters, which are not properly parsed as spaces
                // by email clients, so we can't use it here.
                modifiedUrl.search = modifiedUrl.search
                    .replace(encodeURIComponent("{title}"), encodeURIComponent(currentTitle));
            }
        }

        const mediaParamFound = mediaParams.find(param => modifiedUrl.searchParams.has(param));
        if (mediaParamFound) {
            const ogImageEl = document.querySelector("meta[property='og:image']");
            // Some pages (/profile/user/ID) don't have an image to share.
            if (ogImageEl) {
                // We don't need to encode the media as searchParams does it.
                const media = ogImageEl.content;
                modifiedUrl.searchParams.set(mediaParamFound, media);
            } else {
                modifiedUrl.searchParams.delete(mediaParamFound);
            }
        }

        window.open(
            modifiedUrl.toString(),
            aEl.target,
            "menubar=no,toolbar=no,resizable=yes,scrollbars=yes,height=550,width=600",
        );
    },
});

publicWidget.registry.share = ShareWidget;

export default ShareWidget;
