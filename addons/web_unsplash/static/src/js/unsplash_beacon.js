odoo.define('web_unsplash.beacon', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.UnsplashBeacon = publicWidget.Widget.extend({
    // /!\ To adapt the day the beacon makes sense for backend customizations
    selector: '#wrapwrap',

    /**
     * @override
     */
    start: function () {
        var unsplashImages = _.map(this.$('img[src*="/unsplash/"]'), function (img) {
            // get image id from URL (`http://www.domain.com:1234/unsplash/xYdf5feoI/lion.jpg` -> `xYdf5feoI`)
            return img.src.split('/unsplash/')[1].split('/')[0];
        });
        if (unsplashImages.length) {
            this._rpc({
                route: '/web_unsplash/get_app_id',
            }).then(function (appID) {
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
});
