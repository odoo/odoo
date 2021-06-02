odoo.define('im_support.SupportSession', function (require) {
"use strict";

var session = require('web.session');
var Session = require('web.Session');

/**
 * This module returns an instance of Session which is linked to the Support
 * server, allowing the current instance to communicate with the Support
 * server (CORS).
 */
return new Session(null, session.support_origin, {
    modules: odoo._modules,
    use_cors: true,
});

});
