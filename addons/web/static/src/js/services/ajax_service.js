odoo.define('web.AjaxService', function (require) {
"use strict";

var AbstractService = require('web.AbstractService');
var session = require('web.session');

var AjaxService = AbstractService.extend({
    name: 'ajax',
    rpc: function (route, args) {
        return session.rpc(route, args);
    },
});

return AjaxService;

});
