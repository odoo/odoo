odoo.define("web.public_env", function (require) {
    "use strict";

    const { _t } = require("web.core");
    const rpc = require("web.rpc");

    const qweb = new owl.QWeb({ translateFn: _t });

    function performRPC(params, options) {
        const query = rpc.buildQuery(params);
        return session.rpc(query.route, query.params, options);
    }

    // There should be as much dependencies as possible in the env object.
    // This will allow an easier testing of components.
    // See https://github.com/odoo/owl/blob/master/doc/reference/environment.md#content-of-an-environment
    // for more information on environments.
    return {
        qweb,
        services: {
            rpc: performRPC,
        },
    };
});
