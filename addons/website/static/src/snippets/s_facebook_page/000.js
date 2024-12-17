import { pick } from "@web/core/utils/objects";
import publicWidget from "@web/legacy/js/public/public_widget";
import { debounce } from "@web/core/utils/timing";
import { ObservingCookieWidgetMixin } from "@website/snippets/observing_cookie_mixin";

/* global FB */

const FacebookPageWidget = publicWidget.Widget.extend(ObservingCookieWidgetMixin, {
    selector: '.o_facebook_page',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this.previousWidth = 0;

        const params = pick(this.$el[0].dataset, 'href', 'height', 'tabs', 'small_header', 'hide_cover');
        if (!params.href) {
            return def;
        }

        this._renderFacebookPage(params);
        this.resizeObserver = new ResizeObserver(debounce(this._renderFacebookPage.bind(this, params), 100));
        this.resizeObserver.observe(this.el.parentElement);

        return def;
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Render the Facebook page plugin using the SDK.
     *
     * @private
     * @param {Object} params
     */
    _renderFacebookPage(params) {
        this._deactivateEditorObserver();

        params.width = Math.floor(this.$el.width());
        if (this.previousWidth !== params.width) {
            this.previousWidth = params.width;
            for (const [key, value] of Object.entries(params)) {
                this.$el[0].dataset[key] = value;
            }
            // Initialize the Facebook SDK
            if (typeof FB !== 'undefined') {
                FB.XFBML.parse(this.el);
            }
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
