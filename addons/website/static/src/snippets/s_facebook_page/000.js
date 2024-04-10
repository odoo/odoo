odoo.define('website.s_facebook_page', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var utils = require('web.utils');
const { debounce } = require("@web/core/utils/timing");

const FacebookPageWidget = publicWidget.Widget.extend({
    selector: '.o_facebook_page',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this.previousWidth = 0;

        const params = _.pick(this.$el[0].dataset, 'href', 'id', 'height', 'tabs', 'small_header', 'hide_cover');
        if (!params.href) {
            return def;
        }
        if (params.id) {
            params.href = `https://www.facebook.com/${params.id}`;
        }
        delete params.id;

        this._renderIframe(params);
        this.resizeObserver = new ResizeObserver(debounce(this._renderIframe.bind(this, params), 100));
        this.resizeObserver.observe(this.el.parentElement);

        return def;
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        if (this.iframeEl) {
            this.iframeEl.remove();
        }
        this.resizeObserver.disconnect();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Prepare iframe element & replace it with existing iframe.
     *
     * @private
     * @param {Object} params
    */
    _renderIframe(params) {
        this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();

        params.width = utils.confine(Math.floor(this.$el.width()), 180, 500);
        if (this.previousWidth !== params.width) {
            this.previousWidth = params.width;
            const src = $.param.querystring("https://www.facebook.com/plugins/page.php", params);
            this.iframeEl = Object.assign(document.createElement("iframe"), {
                src: src,
                width: params.width,
                height: params.height,
                css: {
                    border: "none",
                    overflow: "hidden",
                },
                scrolling: "no",
                frameborder: "0",
                allowTransparency: "true",
            });
            this.el.replaceChildren(this.iframeEl);
        }

        this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
    },
});

publicWidget.registry.facebookPage = FacebookPageWidget;

return FacebookPageWidget;
});
