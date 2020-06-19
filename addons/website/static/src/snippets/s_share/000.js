odoo.define('website.s_share', function (require) {
'use strict';

const publicWidget = require('web.public.widget');

const ShareWidget = publicWidget.Widget.extend({
    selector: '.s_share, .oe_share', // oe_share for compatibility

    /**
     * @override
     */
    start: function () {
        var urlRegex = /(\?(?:|.*&)(?:u|url|body)=)(.*?)(&|#|$)/;
        var titleRegex = /(\?(?:|.*&)(?:title|text|subject)=)(.*?)(&|#|$)/;
        var url = encodeURIComponent(window.location.href);
        var title = encodeURIComponent($('title').text());
        this.$('a').each(function () {
            var $a = $(this);
            $a.attr('href', function (i, href) {
                return href.replace(urlRegex, function (match, a, b, c) {
                    return a + url + c;
                }).replace(titleRegex, function (match, a, b, c) {
                    return a + title + c;
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
