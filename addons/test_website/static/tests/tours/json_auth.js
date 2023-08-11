/** @odoo-module **/

import { registry } from "@web/core/registry";
import ajax from "@web/legacy/js/core/ajax";

registry.category("web_tour.tours").add('test_json_auth', {
    test: true,
    steps: () => [{
    trigger: 'body',
    run: async function () {
        await ajax.rpc('/test_get_dbname').then( function (result){
            return ajax.rpc("/web/session/authenticate", {
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
]});
