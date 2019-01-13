odoo.define('web.AbstractService', function (require) {
"use strict";

var Class = require('web.Class');
var Mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');

var AbstractService = Class.extend(Mixins.EventDispatcherMixin, ServicesMixin, {
    dependencies: [],
    init: function (parent) {
        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(parent);
    },
    /**
     * @abstract
     */
    start: function () {},
});

return AbstractService;
});
