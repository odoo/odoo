odoo.define('web.AjaxService', function (require) {
"use strict";

var AbstractService = require('web.AbstractService');
var session = require('web.session');

var AjaxService = AbstractService.extend({
    name: 'ajax',
    rpc: function (route, args, options, target) {
        return $.Deferred(function (def) {
            session.rpc(route, args, options).then(function () {
                if (!target.isDestroyed()) {
                    def.resolve.apply(def, arguments);
                }
            }, function () {
                if (!target.isDestroyed()) {
                    def.reject.apply(def, arguments);
                }
            });
        }).promise();
    },
});

return AjaxService;

});
