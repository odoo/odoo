odoo.define('website_mail_channel.editor', function (require) {
'use strict';

var core = require('web.core');
var rpc = require('web.rpc');
var weContext = require('web_editor.context');
var options = require('web_editor.snippets.options');
var wUtils = require('website.utils');

var _t = core._t;

options.registry.subscribe = options.Class.extend({
    select_mailing_list: function (previewMode, value) {
        var self = this;
        return wUtils.prompt({
            id: "editor_new_subscribe_button",
            window_title: _t("Add a Subscribe Button"),
            select: _t("Discussion List"),
            init: function (field) {
                return rpc.query({
                        model: 'mail.channel',
                        method: 'name_search',
                        args: ['', [['public','=','public']]],
                        context: weContext.get(),
                    });
            },
        }).then(function (mail_channel_id) {
            self.$target.attr("data-id", mail_channel_id);
        });
    },
    onBuilt: function () {
        var self = this;
        this._super();
        this.select_mailing_list("click").fail(function () {
            self.getParent()._removeSnippet();
        });
    },
    cleanForSave: function () {
        this.$target.addClass("hidden");
    },
});
});
