/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import {generateGMapLink, generateGMapIframe} from '@website/js/utils';

publicWidget.registry.Map = publicWidget.Widget.extend({
    selector: '.s_map',

    /**
     * @override
     */
    start() {
        if (!this.el.querySelector('.s_map_embedded')) {
            // The iframe is not found inside the snippet. This is probably due
            // the sanitization of a field during the save, like in a product
            // description field.
            // In such cases, reconstruct the iframe.
            const dataset = this.el.dataset;
            if (dataset.mapAddress) {
                const iframeEl = generateGMapIframe();
                iframeEl.setAttribute('src', generateGMapLink(dataset));
                this.el.querySelector('.s_map_color_filter').before(iframeEl);
            }
        }
        return this._super(...arguments);
    },
});

export default publicWidget.registry.Map;
