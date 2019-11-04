odoo.define('test_website.json_auth', function (require) {
'use strict';

var tour = require('web_tour.tour');
var session = require('web.session')

tour.register('test_json_auth', {
    test: true,
}, [{
    trigger: 'body',
    run: async function () {
        await session.rpc('/test_get_dbname').then( function (result){
            return session.rpc("/web/session/authenticate", {
                db: result,
                login: 'admin',
                password: 'admin'
            });
        });
        window.location.href = window.location.origin;
    },
}, {
    trigger: 'span:contains(Mitchell Admin), span:contains(Administrator)',
    run: function () {},
}
]);
});
