odoo.define('website.s_facebook_page', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var utils = require('web.utils');

const FacebookPageWidget = publicWidget.Widget.extend({
    selector: '.o_facebook_page',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        var params = _.pick(this.$el.data(), 'href', 'height', 'tabs', 'small_header', 'hide_cover', 'show_facepile');
        if (!params.href) {
            return def;
        }
        params.width = utils.confine(Math.floor(this.$el.width()), 180, 500);

        var src = $.param.querystring('https://www.facebook.com/plugins/page.php', params);
        this.$iframe = $('<iframe/>', {
            src: src,
            class: 'o_temp_auto_element',
            width: params.width,
            height: params.height,
            css: {
                border: 'none',
                overflow: 'hidden',
            },
            scrolling: 'no',
            frameborder: '0',
            allowTransparency: 'true',
        });
        this.$el.append(this.$iframe);

        return def;
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);

        if (this.$iframe) {
            this.$iframe.remove();
        }
    },
});

publicWidget.registry.facebookPage = FacebookPageWidget;

return FacebookPageWidget;
});
