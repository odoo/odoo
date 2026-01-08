/** @odoo-module **/

import { registry } from "@web/core/registry";
import { jsonrpc } from "@web/core/network/rpc_service";

registry.category("web_tour.tours").add('test_json_auth', {
    test: true,
    steps: () => [{
    trigger: 'body',
    run: async function () {
        await jsonrpc('/test_get_dbname').then( function (result){
            return jsonrpc("/web/session/authenticate", {
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
