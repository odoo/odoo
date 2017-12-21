odoo.define('web.AbstractService', function (require) {
"use strict";

var Class = require('web.Class');
var Mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');

var AbstractService = Class.extend(Mixins.EventDispatcherMixin, ServicesMixin, {
    Services: [],
    dependencies: [],
    name: null,
    init: function (parent) {
        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(parent);
    },
});

var realExtend = AbstractService.extend;

AbstractService.extend = function () {
    var Service = realExtend.apply(this, arguments);
    AbstractService.prototype.Services.push(Service);
    return Service;
};

return AbstractService;
});
