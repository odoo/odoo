/** @odoo-module */

import publicWidget from 'web.public.widget';

const ShareWidget = publicWidget.Widget.extend({
    selector: '.s_share, .oe_share', // oe_share for compatibility
    events: {
        'click a': '_onShareLinkClick',
    },

    /**
     * @override
     */
    async start() {
        this.URL_REGEX = /(\?(?:|.*&)(?:u|url|body)=)(.*?)(&|#|$)/;
        this.TITLE_REGEX = /(\?(?:|.*&)(?:title|text|subject|description)=)(.*?)(&|#|$)/;
        this.MEDIA_REGEX = /(\?(?:|.*&)(?:media)=)(.*?)(&|#|$)/;

        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        // TODO adapt in master. Ugly way here to fix existing s_share snippets
        // before entering edit mode.
        this.el.classList.add('o_no_link_popover');
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
        const aEl = ev.currentTarget;
        const currentHref = aEl.href;

        // Try and support old use of share snippet as a social link snippet:
        // if the URL does not look like a sharer, then do nothing. This
        // obviously won't cover all cases (people may have added URL that look
        // like sharer but are not but in that case, it was probably already
        // broken before).
        if (!this.URL_REGEX.test(currentHref)
                && !this.TITLE_REGEX.test(currentHref)
                && !this.MEDIA_REGEX.test(currentHref)) {
            return;
        }

        ev.preventDefault();
        ev.stopPropagation();

        const url = encodeURIComponent(window.location.href);
        const title = encodeURIComponent(document.title);

        aEl.href = currentHref
            .replace(this.URL_REGEX, (match, a, b, c) => {
                return a + url + c;
            })
            .replace(this.TITLE_REGEX, function (match, a, b, c) {
                if (aEl.classList.contains('s_share_whatsapp')) {
                    // WhatsApp does not support the "url" GET parameter.
                    // Instead we need to include the url within the passed "text"
                    // parameter, merging everything together, e.g of output:
                    // https://wa.me/?text=%20OpenWood%20Collection%20Online%20Reveal%20%7C%20My%20Website%20http%3A%2F%2Flocalhost%3A8888%2Fevent%2Fopenwood-collection-online-reveal-2021-06-21-2021-06-23-8%2Fregister
                    // For more details, see https://faq.whatsapp.com/general/chats/how-to-use-click-to-chat/
                    return `${a + title}%20${url + c}`;
                }
                return a + title + c;
            });
        const urlObject = new URL(aEl.href);
        if (urlObject.searchParams.has("media")) {
            const ogImageEl = document.querySelector("meta[property='og:image']");
            // Some pages (/profile/user/ID) don't have an image to share.
            if (ogImageEl) {
                const media = encodeURIComponent(ogImageEl.content);
                urlObject.searchParams.set("media", media);
            } else {
                // We don't delete the media parameter in the href in case
                // there is media to share in the next sharer click.
                urlObject.searchParams.delete("media");
            }
        }

        window.open(urlObject.toString(), aEl.target, 'menubar=no,toolbar=no,resizable=yes,scrollbars=yes,height=550,width=600');
    },
});

publicWidget.registry.share = ShareWidget;

export default ShareWidget;
