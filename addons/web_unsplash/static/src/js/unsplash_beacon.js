/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.UnsplashBeacon = publicWidget.Widget.extend({
    // /!\ To adapt the day the beacon makes sense for backend customizations
    selector: '#wrapwrap',

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    /**
     * @override
     */
    start: function () {
        var unsplashImages = Array.from(this.$('img[src*="/unsplash/"]')).map((img) => {
            // get image id from URL (`http://www.domain.com:1234/unsplash/xYdf5feoI/lion.jpg` -> `xYdf5feoI`)
            return img.src.split('/unsplash/')[1].split('/')[0];
        });
        if (unsplashImages.length) {
            this.rpc('/web_unsplash/get_app_id').then(function (appID) {
                if (!appID) {
                    return;
                }
                $.get('https://views.unsplash.com/v', {
                    'photo_id': unsplashImages.join(','),
                    'app_id': appID,
                });
            });
        }
        return this._super.apply(this, arguments);
    },
});
