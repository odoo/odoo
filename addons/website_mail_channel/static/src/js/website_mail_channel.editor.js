odoo.define('website_mail_channel.editor', function (require) {
'use strict';

var core = require('web.core');
var rpc = require('web.rpc');
var base = require('web_editor.base');
var options = require('web_editor.snippets.options');
var website = require('website.website');

var _t = core._t;

options.registry.subscribe = options.Class.extend({
    select_mailing_list: function (type, value) {
        var self = this;
        if (type !== "click") return;
        return website.prompt({
            id: "editor_new_subscribe_button",
            window_title: _t("Add a Subscribe Button"),
            select: _t("Discussion List"),
            init: function (field) {
                return rpc.query({model: 'mail.channel', method: 'name_search'})
                    .args(['', [['public','=','public']]])
                    .withContext(base.get_context())
                    .exec({type: "ajax"});
            },
        }).then(function (mail_channel_id) {
            self.$target.attr("data-id", mail_channel_id);
        });
    },
    drop_and_build_snippet: function() {
        var self = this;
        this._super();
        this.select_mailing_list("click").fail(function () {
            self.editor.on_remove();
        });
    },
    clean_for_save: function () {
        this.$target.addClass("hidden");
    },
});

});
