odoo.define('website.post_link', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
const wUtils = require('website.utils');

publicWidget.registry.postLink = publicWidget.Widget.extend({
    selector: '.post_link',
    events: {
        'click': '_onClickPost',
    },
    _onClickPost: function (ev) {
        ev.preventDefault();
        const url = this.el.dataset.post || this.el.href;
        let data = {};
        for (let [key, value] of Object.entries(this.el.dataset)) {
            if (key.startsWith('post_')) {
                data[key.slice(5)] = value;
            }
        };
        wUtils.sendRequest(url, data);
    },
});

});
