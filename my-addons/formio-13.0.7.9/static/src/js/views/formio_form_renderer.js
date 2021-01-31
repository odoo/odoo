odoo.define('formio.FormRenderer', function (require) {
"use strict";

var BasicRenderer = require('web.BasicRenderer');
var core = require('web.core');
var qweb = core.qweb;

var FormRenderer = BasicRenderer.extend({
    className: "o_form_view",

    init: function (parent, state, params) {
        this._super.apply(this, arguments);
    },

    /**
     * Main entry point for the rendering.
     *
     * @private
     * @override method from BasicRenderer
     * @returns {Deferred}
     */
    _renderView: function () {
        var self = this;
        var form = $(qweb.render('formio.form', {form: self.state.data, context: self.state.context}));
        return $.when.apply($).then(function() {
            self.$el.html(form);
        });
    }
});

return FormRenderer;
});
