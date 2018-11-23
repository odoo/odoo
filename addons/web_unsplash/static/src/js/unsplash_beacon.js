odoo.define('web_unsplash.beacon', function (require) {
'use strict';

var base = require('web_editor.base');
var ajax = require('web.ajax');

base.ready().then(function () {
    var unsplash_images = [];
    _.each($('img[src*="/unsplash/"]'), function (img, index) {
        // get image id from URL (`http://www.domain.com:1234/unsplash/xYdf5feoI/lion.jpg` -> `xYdf5feoI`)
        unsplash_images.push(img.src.split('/unsplash/')[1].split('/')[0]);
    });
    if (unsplash_images.length) {
        ajax.jsonRpc('/web_unsplash/get_app_id', 'call').then(function (appID) {
            if (appID) {
                var unsplash_view_url = 'https://views.unsplash.com/v';
                $.get(unsplash_view_url, {
                    photo_id: unsplash_images.join(','),
                    app_id: appID,
                });
            }
        });
    }
});

});
