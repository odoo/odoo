odoo.define('sale.tour_sale_signature', function (require) {
'use strict';

var tour = require('web_tour.tour');

// This tour relies on data created on the Python test.
tour.register('sale_signature', {
    test: true,
    url: '/my/quotes',
},
[
    {
        content: "open the test SO",
        trigger: 'a:containsExact("test SO")',
    },
    {
        content: "click sign",
        trigger: 'a:contains("Sign")',
    },
    {
        content: "check submit is enabled",
        trigger: '.o_portal_sign_submit:enabled',
        run: function () {},
    },
    {
        content: "click select style",
        trigger: '.o_web_sign_auto_select_style a',
    },
    {
        content: "click style 4",
        trigger: '.o_web_sign_auto_font_selection a:eq(3)',
    },
    {
        content: "click submit",
        trigger: '.o_portal_sign_submit:enabled',
    },
    {
        content: "check it's confirmed",
        trigger: '#quote_content:contains("Thank You")',
    }, {
        trigger: '#quote_content',
        run: function () {
            window.location.href = window.location.origin + '/web';
        },  // Avoid race condition at the end of the tour by returning to the home page.
    },
    {
        trigger: 'nav',
        run: function() {},
    }
]);
});
