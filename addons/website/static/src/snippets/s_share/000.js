odoo.define('website.s_share', function (require) {
'use strict';

const publicWidget = require('web.public.widget');

const ShareWidget = publicWidget.Widget.extend({
    selector: '.s_share, .oe_share', // oe_share for compatibility

    /**
     * @override
     */
    start: function () {
        const urlRegex = /(\?(?:|.*&)(?:u|url|body)=)(.*?)(&|#|$)/;
        const titleRegex = /(\?(?:|.*&)(?:title|text|subject|description)=)(.*?)(&|#|$)/;
        const mediaRegex = /(\?(?:|.*&)(?:media)=)(.*?)(&|#|$)/;
        const url = encodeURIComponent(window.location.href);
        const title = encodeURIComponent($('title').text());
        const media = encodeURIComponent($('meta[property="og:image"]').attr('content'));

        this.$('a').each((index, element) => {
            const $a = $(element);
            $a.attr('href', (i, href) => {
                return href.replace(urlRegex, (match, a, b, c) => {
                    return a + url + c;
                }).replace(titleRegex, function (match, a, b, c) {
                    if ($a.hasClass('s_share_whatsapp')) {
                        // WhatsApp does not support the "url" GET parameter.
                        // Instead we need to include the url within the passed "text" parameter, merging everything together.
                        // e.g of output:
                        // https://wa.me/?text=%20OpenWood%20Collection%20Online%20Reveal%20%7C%20My%20Website%20http%3A%2F%2Flocalhost%3A8888%2Fevent%2Fopenwood-collection-online-reveal-2021-06-21-2021-06-23-8%2Fregister
                        // see https://faq.whatsapp.com/general/chats/how-to-use-click-to-chat/ for more details
                        return a + title + url + c;
                    }
                    return a + title + c;
                }).replace(mediaRegex, (match, a, b, c) => {
                    return a + media + c;
                });
            });
            if ($a.attr('target') && $a.attr('target').match(/_blank/i) && !$a.closest('.o_editable').length) {
                $a.on('click', function () {
                    window.open(this.href, '', 'menubar=no,toolbar=no,resizable=yes,scrollbars=yes,height=550,width=600');
                    return false;
                });
            }
        });

        return this._super.apply(this, arguments);
    },
});

publicWidget.registry.share = ShareWidget;

return ShareWidget;
});
