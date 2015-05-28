odoo.define('website_mail_channel.editor', function (require) {
'use strict';

var core = require('web.core');
var Model = require('web.Model');
var snippet_editor = require('website.snippets.editor');
var website = require('website.website');

var _t = core._t;


snippet_editor.options.subscribe = snippet_editor.Option.extend({
    choose_mailing_list: function (type, value) {
        var self = this;
        if (type !== "click") return;
        return website.prompt({
            id: "editor_new_subscribe_button",
            window_title: _t("Add a Subscribe Button"),
            select: _t("Discussion List"),
            init: function (field) {
                return new Model('mail.group')
                        .call('name_search', ['', [['public','=','public']]], { context: website.get_context() });
            },
        }).then(function (mail_group_id) {
            self.$target.attr("data-id", mail_group_id);
        });
    },
    drop_and_build_snippet: function() {
        var self = this;
        this._super();
        this.choose_mailing_list("click").fail(function () {
            self.editor.on_remove();
        });
    },
    clean_for_save: function () {
        this.$target.addClass("hidden");
    },
});
});
