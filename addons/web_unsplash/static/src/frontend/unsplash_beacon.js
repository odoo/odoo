/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.UnsplashBeacon = publicWidget.Widget.extend({
    // /!\ To adapt the day the beacon makes sense for backend customizations
    selector: '#wrapwrap',

    /**
     * @override
     */
    start: function () {
        const unsplashImages = Array.from(this.el.querySelectorAll('img[src*="/unsplash/"]')).map((img) => {
            // get image id from URL (`http://www.domain.com:1234/unsplash/xYdf5feoI/lion.jpg` -> `xYdf5feoI`)
            return img.src.split('/unsplash/')[1].split('/')[0];
        });
        if (unsplashImages.length) {
            rpc('/web_unsplash/get_app_id').then(function (appID) {
                if (!appID) {
                    return;
                }
                const url = "https://views.unsplash.com/v";
                const params = { photo_id: unsplashImages.join(","), app_id: appID };
                const queryString = new URLSearchParams(params).toString();
                const fullUrl = `${url}?${queryString}`;
                fetch(fullUrl);
            });
        }
        return this._super.apply(this, arguments);
    },
});
