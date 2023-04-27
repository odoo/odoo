odoo.define('auth_password_policy.ChangePassword', function (require) {
"use strict";
var ChangePassword = require('web.ChangePassword');
var policy = require('auth_password_policy');
var Meter = require('auth_password_policy.Meter');

ChangePassword.include({
    events: {
        'input input[name=new_password]': function (e) {
            this._meter.update(e.target.value);
        }
    },
    willStart: function () {
        var _this = this;
        var getPolicy = this._rpc({
            model: 'res.users',
            method: 'get_password_policy'
        }).then(function (p) {
            _this._meter = new Meter(_this, new policy.Policy(p), policy.recommendations);
        });
        return Promise.all([
            this._super.apply(this, arguments),
            getPolicy
        ]);
    },
    start: function () {
        return Promise.all([
            this._meter.insertAfter(this.$('input[name=new_password]')),
            this._super()
        ]);
    }
})
});
