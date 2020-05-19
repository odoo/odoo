odoo.define('website_blog.tags_list', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
const wUtils = require('website.utils');

publicWidget.registry.tagsList = publicWidget.Widget.extend({
    selector: '.tags_list',
    events: {
        'click .one_tag': '_onTagSelection',
    },
    _onTagSelection: function (ev) {
        ev.preventDefault();
        const data = ev.target.dataset;
        wUtils.sendRequest(data.query, {
            'tag': data.tags_list,
        });
    },
});

});
