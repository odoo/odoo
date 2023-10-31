/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { pick } from "@web/core/utils/objects";
import { clamp } from "@web/core/utils/numbers";
import publicWidget from "@web/legacy/js/public/public_widget";

const FacebookPageWidget = publicWidget.Widget.extend({
    selector: '.o_facebook_page',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();

        const params = pick(this.$el[0].dataset, 'href', 'id', 'height', 'tabs', 'small_header', 'hide_cover');
        if (!params.href) {
            return def;
        }
        if (params.id) {
            params.href = `https://www.facebook.com/${params.id}`;
        }
        delete params.id;
        params.width = clamp(Math.floor(this.$el.width()), 180, 500);

        const searchParams = new URLSearchParams(params);
        const src = "https://www.facebook.com/plugins/page.php?" + searchParams;

        this.$iframe = $('<iframe/>', {
            src: src,
            width: params.width,
            height: params.height,
            css: {
                border: 'none',
                overflow: 'hidden',
            },
            scrolling: 'no',
            frameborder: '0',
            allowTransparency: 'true',
            "aria-label": _t("Facebook"),
        });
        this.$el.append(this.$iframe);

        this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
        return def;
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);

        this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();
        if (this.$iframe) {
            this.$iframe.remove();
        }
        this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
    },
});

publicWidget.registry.facebookPage = FacebookPageWidget;

export default FacebookPageWidget;
