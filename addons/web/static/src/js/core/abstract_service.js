odoo.define('web.AbstractService', function (require) {
"use strict";

var Class = require('web.Class');

var AbstractService = Class.extend({
    Services: [],
    name: null,
});

var realExtend = AbstractService.extend;

AbstractService.extend = function() {
    var Service = realExtend.apply(this, arguments);
    AbstractService.prototype.Services.push(Service);
    return Service;
};

return AbstractService;
});
