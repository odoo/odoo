odoo.define('website_mail_channel.editor', function (require) {
'use strict';

var core = require('web.core');
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
                return self._rpc({
                    model: 'mail.channel',
                    method: 'name_search',
                    args: ['', [['public', '=', 'public']]],
                });
            },
        }).then(function (result) {
            self.$target.attr("data-id", result.val);
        });
    },
    onBuilt: function () {
        var self = this;
        this._super();
        this.select_mailing_list("click").guardedCatch(function () {
            self.getParent().removeSnippet();
        });
    },
    cleanForSave: function () {
        this.$target.addClass('d-none');
    },
});
});
