odoo.define('web.AjaxService', function (require) {
"use strict";

var AbstractService = require('web.AbstractService');
var session = require('web.session');

var AjaxService = AbstractService.extend({
    name: 'ajax',
    rpc: function (route, args, options) {
        return session.rpc(route, args, options);
    },
});

return AjaxService;

});
