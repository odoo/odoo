odoo.define('website.s_share', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
var config = require('web.config');

const ShareWidget = publicWidget.Widget.extend({
    selector: '.s_share, .oe_share', // oe_share for compatibility

    /**
     * @override
     */
    start: function () {
        let urlRegex = /(\?(?:|.*&)(?:u|url|body)=)(.*?)(&|#|$)/,
            titleRegex = /(\?(?:|.*&)(?:title|text|subject|description)=)(.*?)(&|#|$)/,
            mediaRegex = /(\?(?:|.*&)(?:media)=)(.*?)(&|#|$)/,
            url = encodeURIComponent(window.location.href),
            title = encodeURIComponent($('title').text()),
            media = encodeURIComponent($('meta[property="og:image"]').attr('content'));

        this.$('a').each((index, element) => {
            let $a = $(element);
            $a.attr('href', (i, href) => {
                return href.replace(urlRegex, (match, a, b, c) => {
                    return a + url + c;
                }).replace(titleRegex, (match, a, b, c) => {
                    return ($a.hasClass('s_share_whatsapp') ? a + title + url + c : a + title + c);
                }).replace(mediaRegex, (match, a, b, c) => {
                    return a + media + c;
                });
            });
            if ($a.attr('target') && $a.attr('target').match(/_blank/i) && !$a.closest('.o_editable').length) {
                $a.on('click', (ev) => {
                    if ($a.hasClass('s_share_whatsapp') && config.device.isMobileDevice){
                       ev.currentTarget.href = ev.currentTarget.href.replace('https://web.whatsapp.com', 'whatsapp:/');
                    }
                    window.open(ev.currentTarget.href, '', 'menubar=no,toolbar=no,resizable=yes,scrollbars=yes,height=550,width=600');
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
