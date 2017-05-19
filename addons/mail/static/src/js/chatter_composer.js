odoo.define('mail.ChatterComposer', function (require) {
"use strict";

// var chat_manager = require('mail.chat_manager');
var composer = require('mail.composer');
var utils = require('mail.utils');

var core = require('web.core');
var view_dialogs = require('web.view_dialogs');

var _t = core._t;

// Chat Composer for the Chatter
//
// Extends the basic Composer Widget to add 'suggested partner' layer (open
// popup when suggested partner is selected without email, or other
// informations), and the button to open the full composer wizard.
var ChatterComposer = composer.BasicComposer.extend({
    template: 'mail.chatter.ChatComposer',

    init: function (parent, model, suggested_partners, options) {
        this._super(parent, options);
        this.model = model;
        this.suggested_partners = suggested_partners;
        this.options = _.defaults(this.options, {
            display_mode: 'textarea',
            record_name: false,
            is_log: false,
        });
        if (this.options.is_log) {
            this.options.send_text = _t('Log');
        }
        this.events = _.extend(this.events, {
            'click .o_composer_button_full_composer': 'on_open_full_composer',
        });
    },

    should_send: function () {
        return false;
    },

    preprocess_message: function () {
        var self = this;
        var def = $.Deferred();
        this._super().then(function (message) {
            message = _.extend(message, {
                subtype: 'mail.mt_comment',
                message_type: 'comment',
                content_subtype: 'html',
                context: self.context,
            });

            // Subtype
            if (self.options.is_log) {
                message.subtype = 'mail.mt_note';
            }

            // Partner_ids
            if (!self.options.is_log) {
                var checked_suggested_partners = self.get_checked_suggested_partners();
                self.check_suggested_partners(checked_suggested_partners).done(function (partner_ids) {
                    message.partner_ids = (message.partner_ids || []).concat(partner_ids);
                    // update context
                    message.context = _.defaults({}, message.context, {
                        mail_post_autofollow: true,
                    });
                    def.resolve(message);
                });
            } else {
                def.resolve(message);
            }

        });

        return def;
    },

    clear_composer_on_send: function() {
        /* chatter don't clear message on sent but after successful sent */
    },

    /**
    * Send the message on SHIFT+ENTER, but go to new line on ENTER
    */
    prevent_send: function (event) {
        return !event.shiftKey;
    },

    /**
     * Get the list of selected suggested partners
     * @returns Array() : list of 'recipient' selected partners (may not be created in db)
     **/
    get_checked_suggested_partners: function () {
        var self = this;
        var checked_partners = [];
        this.$('.o_composer_suggested_partners input:checked').each(function() {
            var full_name = $(this).data('fullname');
            checked_partners = checked_partners.concat(_.filter(self.suggested_partners, function(item) {
                return full_name === item.full_name;
            }));
        });
        return checked_partners;
    },

    /**
     * Check the additional partners (not necessary registered partners), and open a popup form view
     * for the ones who informations is missing.
     * @param Array : list of 'recipient' partners to complete informations or validate
     * @returns Deferred resolved with the list of checked suggested partners (real partner)
     **/
    check_suggested_partners: function (checked_suggested_partners) {
        var self = this;
        var check_done = $.Deferred();

        var recipients = _.filter(checked_suggested_partners, function (recipient) { return recipient.checked; });
        var recipients_to_find = _.filter(recipients, function (recipient) { return (! recipient.partner_id); });
        var names_to_find = _.pluck(recipients_to_find, 'full_name');
        var recipients_to_check = _.filter(recipients, function (recipient) { return (recipient.partner_id && ! recipient.email_address); });
        var recipient_ids = _.pluck(_.filter(recipients, function (recipient) { return recipient.partner_id && recipient.email_address; }), 'partner_id');

        var names_to_remove = [];
        var recipient_ids_to_remove = [];

        // have unknown names -> call message_get_partner_info_from_emails to try to find partner_id
        var def;
        if (names_to_find.length > 0) {
            def = this._rpc({
                    model: this.model,
                    method: 'message_partner_info_from_emails',
                    args: [[this.context.default_res_id], names_to_find],
                });
        }

        // for unknown names + incomplete partners -> open popup - cancel = remove from recipients
        $.when(def).pipe(function (result) {
            result = result || [];
            var emails_deferred = [];
            var recipient_popups = result.concat(recipients_to_check);

            _.each(recipient_popups, function (partner_info) {
                var deferred = $.Deferred();
                emails_deferred.push(deferred);

                var partner_name = partner_info.full_name;
                var partner_id = partner_info.partner_id;
                var parsed_email = utils.parse_email(partner_name);

                var dialog = new view_dialogs.FormViewDialog(self, {
                    res_model: 'res.partner',
                    res_id: partner_id,
                    context: {
                        force_email: true,
                        ref: "compound_context",
                        default_name: parsed_email[0],
                        default_email: parsed_email[1],
                    },
                    title: _t("Please complete partner's informations"),
                    disable_multiple_selection: true,
                }).open();
                dialog.on('closed', self, function () {
                    deferred.resolve();
                });
                dialog.opened().then(function () {
                    dialog.form_view.on('on_button_cancel', self, function () {
                        names_to_remove.push(partner_name);
                        if (partner_id) {
                            recipient_ids_to_remove.push(partner_id);
                        }
                    });
                });
            });
            $.when.apply($, emails_deferred).then(function () {
                var new_names_to_find = _.difference(names_to_find, names_to_remove);
                var def;
                if (new_names_to_find.length > 0) {
                    def = self._rpc({
                            model: self.model,
                            method: 'message_partner_info_from_emails',
                            args: [[self.context.default_res_id], new_names_to_find, true],
                        });
                }
                $.when(def).pipe(function (result) {
                    result = result || [];
                    var recipient_popups = result.concat(recipients_to_check);
                    _.each(recipient_popups, function (partner_info) {
                        if (partner_info.partner_id && _.indexOf(partner_info.partner_id, recipient_ids_to_remove) === -1) {
                            recipient_ids.push(partner_info.partner_id);
                        }
                    });
                }).pipe(function () {
                    check_done.resolve(recipient_ids);
                });
            });
        });
        return check_done;
    },

    on_open_full_composer: function() {
        if (!this.do_check_attachment_upload()){
            return false;
        }

        var self = this;
        var recipient_done = $.Deferred();
        if (this.options.is_log) {
            recipient_done.resolve([]);
        } else {
            var checked_suggested_partners = this.get_checked_suggested_partners();
            recipient_done = this.check_suggested_partners(checked_suggested_partners);
        }
        recipient_done.then(function (partner_ids) {
            var context = {
                default_parent_id: self.id,
                default_body: utils.get_text2html(self.$input.val()),
                default_attachment_ids: _.pluck(self.get('attachment_ids'), 'id'),
                default_partner_ids: partner_ids,
                default_is_log: self.options.is_log,
                mail_post_autofollow: true,
            };

            if (self.context.default_model && self.context.default_res_id) {
                context.default_model = self.context.default_model;
                context.default_res_id = self.context.default_res_id;
            }

            var action = {
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: context,
            };
            self.do_action(action, {
                on_close: self.trigger.bind(self, 'need_refresh'),
            }).then(self.trigger.bind(self, 'close_composer'));
        });
    }
});

return ChatterComposer;

});