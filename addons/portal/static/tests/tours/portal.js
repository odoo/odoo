odoo.define('portal.tour', function (require) {
'use strict';

var tour = require("web_tour.tour");

tour.register('portal_load_homepage', {
    test: true,
    url: '/my',
},
    [
        {
            content: "Check portal is loaded",
            trigger: 'a[href*="/my/account"]:contains("My Account"):first',
        },
        {
            content: "Load my account details",
            trigger: 'span[itemprop*="name"]:first:contains("Joel Willis")'
        }
    ]
);

});
