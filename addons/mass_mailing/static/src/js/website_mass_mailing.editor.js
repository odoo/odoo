odoo.define('website_mass_mailing.editor', ['web.core', 'website.editor', 'website.snippet.editor', 'website.website'], function (require) {
'use strict';

var core = require('web.core');
var editor = require('website.editor');
var snippet_editor = require('website.snippet.editor');
var website = require('website.website');

var _t = core._t;

snippet_editor.options.mailing_list_subscribe = snippet_editor.Option.extend({
    choose_mailing_list: function (type, value) {
        var self = this;
        if (type !== "click") return;
        return website.prompt({
            id: "editor_new_mailing_list_subscribe_button",
            window_title: _t("Add a Newsletter Subscribe Button"),
            select: _t("Newsletter"),
            init: function (field) {
                return website.session.model('mail.mass_mailing.list')
                        .call('name_search', ['', []], { context: website.get_context() });
            },
        }).then(function (mailing_list_id) {
            self.$target.attr("data-list-id", mailing_list_id);
        });
    },
    drop_and_build_snippet: function() {
        var self = this;
        this._super();
        this.choose_mailing_list('click').fail(function () {
            self.editor.on_remove($.Event( "click" ));
        });
    },
    clean_for_save: function () {
        this.$target.addClass("hidden");
    },
});

website.snippet.options.newsletter_popup = website.snippet.Option.extend({
    select_mailing_list: function (type) {
        var self = this;
        if (type !== "click") return;
        return website.prompt({
            id: "editor_new_mailing_list_subscribe_popup",
            window_title: _t("Add a Newsletter Subscribe Popup"),
            select: _t("Newsletter"),
            init: function () {
                return website.session.model('mail.mass_mailing.list')
                        .call('name_search', [], { context: website.get_context() });
            },
        }).then(function (mailing_list_id) {
            openerp.jsonRpc('/web/dataset/call', 'call', {
                model: 'mail.mass_mailing.list',
                method: 'read',
                args: [[parseInt(mailing_list_id)], ['popup_content'], website.get_context()],
            }).then(function (data) {
                self.$target.find(".o_popup_content_dev").empty();
                if (data && data[0].popup_content) {
                    $(data[0].popup_content).appendTo(self.$target.find(".o_popup_content_dev"));
                }
            });
            self.$target.attr("data-list-id", mailing_list_id);
        });
    },
    drop_and_build_snippet: function() {
        var self = this;
        this._super();
        this.select_mailing_list('click').fail(function () {
            self.editor.on_remove($.Event( "click" ));
        });
    },
});

editor.EditorBar.include({
    edit: function () {
        this._super();
        $('body').on('click','#edit_dialog',_.bind(this.edit_dialog, this.rte.editor));
    },
    save : function() {
        var $target = $('#wrapwrap').find('#o_newsletter_popup');
        if ($target && $target.length) {
            $target.modal('hide');
            $target.css("display", "none");
            $('.o_popup_bounce_small').show();
            if (!$target.find('.o_popup_content_dev').length) {
                $target.find('.o_popup_modal_body').prepend($('<div class="o_popup_content_dev" data-oe-placeholder="Type Here ..."></div>'));
            }
            var content = $('#wrapwrap .o_popup_content_dev').html();
            var newsletter_id = $target.parent().attr('data-list-id');
            openerp.jsonRpc('/web/dataset/call', 'call', {
                model: 'mail.mass_mailing.list',
                method: 'write',
                args: [parseInt(newsletter_id),
                   {'popup_content':content},
                   website.get_context()],
            });
        }
        return this._super();
    },
    edit_dialog : function() {
        $('#wrapwrap').find('#o_newsletter_popup').modal('show');
        $('.o_popup_bounce_small').hide();
        $('.modal-backdrop').css("z-index", "0");
    },
});

});


