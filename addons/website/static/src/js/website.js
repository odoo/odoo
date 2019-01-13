odoo.define('website.website', function (require) {
'use strict';

var weContext = require('web_editor.context');

var weGetContext = weContext.get;
weContext.get = function (context) {
    var html = document.documentElement;
    return _.extend({
        website_id: html.getAttribute('data-website-id') | 0,
    }, weGetContext(context), context);
};
});

odoo.define('website.website_modal', function (require) {
'use strict';

    require('web.dom_ready');

    $('body').on('shown.bs.modal', function (e) {
        $(e.target).addClass('modal_shown');
    });
});
