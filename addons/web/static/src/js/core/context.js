odoo.define('web.Context', function (require) {
"use strict";

var Class = require('web.Class');
var pyeval = require('web.pyeval');

var Context = Class.extend({
    init: function () {
        this.__ref = "compound_context";
        this.__contexts = [];
        this.__eval_context = null;
        var self = this;
        _.each(arguments, function (x) {
            self.add(x);
        });
    },
    add: function (context) {
        this.__contexts.push(context);
        return this;
    },
    set_eval_context: function (eval_context) {
        this.__eval_context = eval_context;
        return this;
    },
    get_eval_context: function () {
        return this.__eval_context;
    },
    eval: function () {
        return pyeval.eval('context', this);
    },
});

return Context;

});
