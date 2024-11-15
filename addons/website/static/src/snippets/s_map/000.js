import publicWidget from '@web/legacy/js/public/public_widget';
import weUtils from "@web_editor/js/common/utils";
import { ObservingCookieWidgetMixin } from "@website/snippets/observing_cookie_mixin";

publicWidget.registry.Map = publicWidget.Widget.extend(ObservingCookieWidgetMixin, {
    selector: '.s_map',

    /**
     * @override
     */
    start() {
        if (!this.el.querySelector('.s_map_embedded')) {
            // The iframe is not found inside the snippet. This is probably due
            // to the sanitization of a field during the save, like in a product
            // description field.
            // In such cases, reconstruct the iframe.
            const dataset = this.el.dataset;
            if (dataset.mapAddress) {
                const iframeEl = weUtils.generateGMapIframe();
                this.el.querySelector('.s_map_color_filter').before(iframeEl);
                this._manageIframeSrc(this.el, weUtils.generateGMapLink(dataset));
            }
        }
        return this._super(...arguments);
    },
});

export default publicWidget.registry.Map;
