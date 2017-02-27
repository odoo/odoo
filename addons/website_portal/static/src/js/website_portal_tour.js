odoo.define('website_portal.tour', function (require) {
'use strict';

var tour = require("web_tour.tour");
var base = require("web_editor.base");

tour.register('portal_load_homepage', {
    test: true,
    url: '/my',
    wait_for: base.ready()
},
    [
        {
            content: "Check portal is loaded",
            trigger: 'a[href*="/my/account"]:contains("Change"):first',
        },
        {
            content: "Load my account details",
            trigger: 'body:contains("Contact Details")',
        }
    ]
);

});
