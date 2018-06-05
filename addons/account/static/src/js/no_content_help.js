odoo.define('account.noContentHelp', function (require) {
"use strict";

var BasicRenderer = require('web.BasicRenderer');
var noContentHelpWidget = require('web.noContentHelpWidget');

BasicRenderer.include({
    _renderNoContentHelper: function () {
        if (this.state.model === "account.invoice") {
            var noContentHelp = new noContentHelpWidget(this, {
                initialNoContentHelp: this.noContentHelp,
                context: _.extend(this.state.context, {'force_reload_help': true}),
                model: this.state.model,
            });
            var $noContentHelp = $('<div>')
            .addClass('o_view_nocontent');
            noContentHelp.appendTo($noContentHelp);
            return $noContentHelp;
        } else {
            return this._super();
        }
    },
});
});