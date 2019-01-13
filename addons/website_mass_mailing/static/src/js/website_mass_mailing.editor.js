odoo.define('website_mass_mailing.editor', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var rpc = require('web.rpc');
var weContext = require('web_editor.context');
var web_editor = require('web_editor.editor');
var options = require('web_editor.snippets.options');
var wUtils = require('website.utils');
var _t = core._t;

var mass_mailing_common = options.Class.extend({
    popup_template_id: "editor_new_mailing_list_subscribe_button",
    popup_title: _t("Add a Newsletter Subscribe Button"),
    select_mailing_list: function (previewMode, value) {
        var self = this;
        var def = wUtils.prompt({
            'id': this.popup_template_id,
            'window_title': this.popup_title,
            'select': _t("Newsletter"),
            'init': function (field) {
                return rpc.query({
                        model: 'mail.mass_mailing.list',
                        method: 'name_search',
                        args: ['', []],
                        context: weContext.get(), // TODO use this._rpc
                    });
            },
        });
        def.then(function (mailing_list_id) {
            self.$target.attr("data-list-id", mailing_list_id);
        });
        return def;
    },
    onBuilt: function () {
        var self = this;
        this._super();
        this.select_mailing_list('click').fail(function () {
            self.getParent()._onRemoveClick($.Event( "click" ));
        });
    },
});

options.registry.mailing_list_subscribe = mass_mailing_common.extend({
    cleanForSave: function () {
        this.$target.addClass('d-none');
    },
});

options.registry.newsletter_popup = mass_mailing_common.extend({
    popup_template_id: "editor_new_mailing_list_subscribe_popup",
    popup_title: _t("Add a Newsletter Subscribe Popup"),
    select_mailing_list: function (previewMode, value) {
        var self = this;
        return this._super(previewMode, value).then(function (mailing_list_id) {
            self._rpc({
                model: 'mail.mass_mailing.list',
                method: 'read',
                args: [[parseInt(mailing_list_id)], ['popup_content']],
            }).then(function (data) {
                self.$target.find(".o_popup_content_dev").empty();
                if (data && data[0].popup_content) {
                    $(data[0].popup_content).appendTo(self.$target.find(".o_popup_content_dev"));
                }
            });
        });
    },
});

web_editor.Class.include({
    start: function () {
        $('body').on('click','#edit_dialog',_.bind(this.edit_dialog, this.rte.editor));
        return this._super();
    },
    save: function () {
        var $target = $('#wrapwrap').find('#o_newsletter_popup');
        if ($target && $target.length) {
            $target.modal('hide');
            $target.css("display", "none");
            $('.o_popup_bounce_small').show();
            if (!$target.find('.o_popup_content_dev').length) {
                $target.find('.o_popup_modal_body').prepend($('<div class="o_popup_content_dev" data-oe-placeholder="' + _t("Type Here ...") + '"></div>'));
            }
            var content = $('#wrapwrap .o_popup_content_dev').html();
            var newsletter_id = $target.parent().attr('data-list-id');
            this._rpc({
                model: 'mail.mass_mailing.list',
                method: 'write',
                args: [
                    parseInt(newsletter_id),
                    {'popup_content':content},
                ],
            });
        }
        return this._super.apply(this, arguments);
    },
    edit_dialog: function () {
        $('#wrapwrap').find('#o_newsletter_popup').modal('show');
        $('.o_popup_bounce_small').hide();
        $('.modal-backdrop').css("z-index", "0");
    },
});
});
