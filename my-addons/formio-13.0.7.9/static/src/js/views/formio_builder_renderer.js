odoo.define('formio.BuilderRenderer', function (require) {
"use strict";

var BasicRenderer = require('web.BasicRenderer');
var core = require('web.core');
var qweb = core.qweb;

var BuilderRenderer = BasicRenderer.extend({
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
        var builder = $(qweb.render('formio.builder', {builder: self.state.data, context: self.state.context}));
        return $.when.apply($).then(function() {
            self.$el.html(builder);
        });
    }
});

return BuilderRenderer;
});
