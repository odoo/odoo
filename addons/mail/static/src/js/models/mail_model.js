odoo.define('mail.Model', function (require) {
"use strict";

var Class = require('web.Class');
var Mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');

var MailModel = Class.extend(Mixins.EventDispatcherMixin, ServicesMixin, {
    /**
     * @param {mail.Manager} parent
     */
    init: function (parent) {
        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(parent);
    },
});

return MailModel;

});
