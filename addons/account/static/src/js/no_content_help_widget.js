odoo.define('web.noContentHelpWidget', function (require) {
"use strict";
var BasicRenderer = require('web.BasicRenderer');
var Widget = require('web.Widget');

var noContentHelpWidget = Widget.extend({
    events: {
        "click a": "onClickEmailAlias",
    },
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.modelName = 'account.invoice';
        this.initialNoContentHelp = params.initialNoContentHelp;
        this.context = params.context;
    },
    willStart: function () {
        var self = this;
        var $noContent = '';
        var ctx = _.extend(this.context, {'force_reload_help': true})
        return this._rpc({
            model: this.modelName,
            method: 'get_empty_list_help',
            args: [this.initialNoContentHelp],
            context: this.context,
        }).then(function (result) {
            self.noContentHelp = result;
        });
    },
    start: function () {
        this.$el.addClass('o_nocontent_help')
            .html(this.noContentHelp).addClass('o_nocontent_help');
        return this._super.apply(this, arguments);
    },
    onClickEmailAlias: function (event) {
        event.preventDefault();
        var id = $(event.target).data('oe-id');
        if (id) {
            this.trigger_up('redirect', {
                res_id: id,
                res_model: $(event.target).data('oe-model'),
            });
        }
    },
});

BasicRenderer.include({
    _renderNoContentHelper: function () {
        if (this.state.model === "account.invoice") {
            var noContentHelp = new noContentHelpWidget(this, {
                initialNoContentHelp: this.noContentHelp,
                context: this.state.context,
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