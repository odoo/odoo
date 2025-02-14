/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { pick } from "@web/core/utils/objects";
import { clamp } from "@web/core/utils/numbers";
import publicWidget from "@web/legacy/js/public/public_widget";
import { debounce } from "@web/core/utils/timing";
import { ObservingCookieWidgetMixin } from "@website/snippets/observing_cookie_mixin";

const FacebookPageWidget = publicWidget.Widget.extend(ObservingCookieWidgetMixin, {
    selector: '.o_facebook_page',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this.previousWidth = 0;

        // Making the snippet non-editable.
        // TODO adapt xml changes by adding "o_not_editable" class
        // to s_facebook_page snippet in master.
        this.el.classList.add("o_not_editable");

        const params = pick(this.$el[0].dataset, 'href', 'id', 'height', 'tabs', 'small_header', 'hide_cover');
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
            this._deactivateEditorObserver();
            this.iframeEl.remove();
            this._activateEditorObserver();
            this.resizeObserver.disconnect();
        }
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
        this._deactivateEditorObserver();

        params.width = clamp(Math.floor(this.$el.width()), 180, 500);
        if (this.previousWidth !== params.width) {
            this.previousWidth = params.width;
            const searchParams = new URLSearchParams(params);
            const src = "https://www.facebook.com/plugins/page.php?" + searchParams;
            this.iframeEl = Object.assign(document.createElement("iframe"), {
                scrolling: "no",
            });
            // TODO: remove, the "scrolling", "frameborder" and
            // "allowTransparency" attributes in master as they are deprecated.
            // Also put the width and height as iframe attribute.
            this.iframeEl.setAttribute("frameborder", "0");
            this.iframeEl.setAttribute("allowTransparency", "true");
            this.iframeEl.setAttribute("style", `width: ${params.width}px; height: ${params.height}px; border: none; overflow: hidden;`);
            this.iframeEl.setAttribute("aria-label", _t("Facebook"));
            this.el.replaceChildren(this.iframeEl);
            this._manageIframeSrc(this.el, src);
        }

        this._activateEditorObserver();
    },

    /**
     * Activates the editor observer if it exists.
     */
    _activateEditorObserver() {
        this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
    },

    /**
     * Deactivates the editor observer if it exists.
     */
    _deactivateEditorObserver() {
        this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();
    },
});

publicWidget.registry.facebookPage = FacebookPageWidget;

export default FacebookPageWidget;
