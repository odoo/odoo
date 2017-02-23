odoo.define('mail.Chatter', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');
var composer = require('mail.composer');
var ChatThread = require('mail.ChatThread');
var utils = require('mail.utils');

var config = require('web.config');
var core = require('web.core');
var form_common = require('web.form_common');
var framework = require('web.framework');
var pyeval = require('web.pyeval');
var Model = require("web.Model");
var web_utils = require('web.utils');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;

// -----------------------------------------------------------------------------
// Chat Composer for the Chatter
//
// Extends the basic Composer Widget to add 'suggested partner' layer (open
// popup when suggested partner is selected without email, or other
// informations), and the button to open the full composer wizard.
// -----------------------------------------------------------------------------
var ChatterComposer = composer.BasicComposer.extend({
    template: 'mail.chatter.ChatComposer',

    init: function (parent, dataset, options) {
        this._super(parent, options);
        this.thread_dataset = dataset;
        this.suggested_partners = [];
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

    willStart: function () {
        if (this.options.is_log) {
            return this._super.apply(this, arguments);
        }
        return $.when(this._super.apply(this, arguments), this.message_get_suggested_recipients());
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

    message_get_suggested_recipients: function () {
        var self = this;
        var email_addresses = _.pluck(this.suggested_partners, 'email_address');
        return this.thread_dataset
            .call('message_get_suggested_recipients', [[this.context.default_res_id], this.context])
            .done(function (suggested_recipients) {
                var thread_recipients = suggested_recipients[self.context.default_res_id];
                _.each(thread_recipients, function (recipient) {
                    var parsed_email = utils.parse_email(recipient[1]);
                    if (_.indexOf(email_addresses, parsed_email[1]) === -1) {
                        self.suggested_partners.push({
                            checked: true,
                            partner_id: recipient[0],
                            full_name: recipient[1],
                            name: parsed_email[0],
                            email_address: parsed_email[1],
                            reason: recipient[2],
                        });
                    }
                });
            });
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
        var find_done = $.Deferred();
        if (names_to_find.length > 0) {
            find_done = self.thread_dataset.call('message_partner_info_from_emails', [[this.context.default_res_id], names_to_find]);
        } else {
            find_done.resolve([]);
        }

        // for unknown names + incomplete partners -> open popup - cancel = remove from recipients
        $.when(find_done).pipe(function (result) {
            var emails_deferred = [];
            var recipient_popups = result.concat(recipients_to_check);

            _.each(recipient_popups, function (partner_info) {
                var deferred = $.Deferred();
                emails_deferred.push(deferred);

                var partner_name = partner_info.full_name;
                var partner_id = partner_info.partner_id;
                var parsed_email = utils.parse_email(partner_name);

                var dialog = new form_common.FormViewDialog(self, {
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
                    dialog.view_form.on('on_button_cancel', self, function () {
                        names_to_remove.push(partner_name);
                        if (partner_id) {
                            recipient_ids_to_remove.push(partner_id);
                        }
                    });
                });
            });
            $.when.apply($, emails_deferred).then(function () {
                var new_names_to_find = _.difference(names_to_find, names_to_remove);
                find_done = $.Deferred();
                if (new_names_to_find.length > 0) {
                    find_done = self.thread_dataset.call('message_partner_info_from_emails', [[self.context.default_res_id], new_names_to_find, true]);
                } else {
                    find_done.resolve([]);
                }
                $.when(find_done).pipe(function (result) {
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

            self.do_action({
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: context,
            }, {
                on_close: function() {
                    self.trigger('need_refresh');
                    var parent = self.getParent();
                    chat_manager.get_messages({model: parent.model, res_id: parent.res_id});
                },
            }).then(self.trigger.bind(self, 'close_composer'));
        });
    }
});

// -----------------------------------------------------------------------------
// Document Chatter ('mail_thread' widget)
//
// Since it is displayed on a form view, it extends 'AbstractField' widget.
// -----------------------------------------------------------------------------
var Chatter = form_common.AbstractField.extend({
    template: 'mail.Chatter',

    events: {
        'click .o_chatter_button_new_message': 'on_open_composer_new_message',
        'click .o_chatter_button_log_note': 'on_open_composer_log_note',
        'click .o_activity_schedule': 'on_activity_schedule',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.model = this.view.dataset.model;
        this.res_id = undefined;
        this.context = this.options.context || {};
        this.dp = new web_utils.DropPrevious();
        // extends display options
        this.options = _.extend(this.options || {}, {
            'display_activity_button': this.field_manager.fields.activity_ids
        });
    },

    willStart: function () {
        return chat_manager.is_ready;
    },

    start: function () {
        var self = this;

        // Hide the chatter in 'create' mode
        this.view.on("change:actual_mode", this, this.check_visibility);
        this.check_visibility();
        var $container = this.$el.parent();
        if ($container.hasClass('oe_chatter')) {
            this.$el
                .addClass($container.attr("class"))
                .unwrap();
        }

        // Move the follower's widget (if any) inside the chatter
        this.followers = this.field_manager.fields.message_follower_ids;
        if (this.followers) {
            this.$('.o_chatter_topbar').append(this.followers.$el);
            this.followers.on('redirect', chat_manager, chat_manager.redirect);
            this.followers.on('followers_update', this, this.on_followers_update);
        }

        // Move the activities widget (if any) inside the chatter
        this.activities = this.field_manager.fields.activity_ids
        if (this.activities) {
            this.$('.o_chatter_topbar').after(this.activities.$el);
        }

        this.thread = new ChatThread(this, {
            display_order: ChatThread.ORDER.DESC,
            display_document_link: false,
            display_needactions: false,
            squash_close_messages: false,
        });
        this.thread.on('load_more_messages', this, this.load_more_messages);
        this.thread.on('toggle_star_status', this, function (message_id) {
            chat_manager.toggle_star_status(message_id);
        });
        this.thread.on('redirect', chat_manager, chat_manager.redirect);
        this.thread.on('redirect_to_channel', this, this.on_channel_redirect);

        this.ready = $.Deferred();

        var def1 = this._super.apply(this, arguments);
        var def2 = this.thread.appendTo(this.$el);

        return $.when(def1, def2).then(function () {
            chat_manager.bus.on('new_message', self, self.on_new_message);
            chat_manager.bus.on('update_message', self, self.on_update_message);
            self.ready.resolve();
        });
    },

    check_visibility: function () {
        this.set({"force_invisible": this.view.get("actual_mode") === "create"});
    },

    fetch_and_render_thread: function (ids, options) {
        var self = this;
        options = options || {};
        options.ids = ids;

        // Ensure that only the last loaded thread is rendered to prevent displaying the wrong thread
        var fetch_def = this.dp.add(chat_manager.get_messages(options));

        // Empty thread and display a spinner after 1s to indicate that it is loading
        this.thread.$el.empty();
        web_utils.reject_after(web_utils.delay(1000), fetch_def).then(function () {
            self.thread.$el.append(QWeb.render('Spinner'));
        });

        return fetch_def.then(function (raw_messages) {
            self.thread.render(raw_messages, {display_load_more: raw_messages.length < ids.length});
        });
    },

    on_post_message: function (message) {
        var self = this;
        var options = {model: this.model, res_id: this.res_id};
        chat_manager
            .post_message(message, options)
            .then(function () {
                self.close_composer(true);
                if (message.partner_ids.length) {
                    self.refresh_followers(); // refresh followers' list
                }
            })
            .fail(function () {
                self.do_notify(_t('Sending Error'), _t('Your message has not been sent.'));
            });
    },

    /**
     * When a message is correctly posted, fetch its data to render it
     * @param {Number} message_id : the identifier of the new posted message
     * @returns {Deferred}
     */
    on_new_message: function (message) {
        if (message.model === this.model && message.res_id === this.res_id) {
            this.msg_ids.unshift(message.id);
            this.fetch_and_render_thread(this.msg_ids);
        }
    },

    on_update_message: function (message) {
        if (message.model === this.model && message.res_id === this.res_id) {
            this.fetch_and_render_thread(this.msg_ids);
        }
    },

    on_channel_redirect: function (channel_id) {
        var self = this;
        var def = chat_manager.join_channel(channel_id);
        $.when(def).then(function () {
            // Execute Discuss client action with 'channel' as default channel
            self.do_action('mail.mail_channel_action_client_chat', {active_id: channel_id});
        });
    },

    on_followers_update: function (followers) {
        this.mention_suggestions = [];
        var self = this;
        var prefetched_partners = chat_manager.get_mention_partner_suggestions();
        var follower_suggestions = [];
        _.each(followers, function (follower) {
            if (follower.res_model === 'res.partner') {
                follower_suggestions.push({
                    id: follower.res_id,
                    name: follower.name,
                    email: follower.email,
                });
            }
        });
        if (follower_suggestions.length) {
            this.mention_suggestions.push(follower_suggestions);
        }
        _.each(prefetched_partners, function (partners) {
            self.mention_suggestions.push(_.filter(partners, function (partner) {
                return !_.findWhere(follower_suggestions, { id: partner.id });
            }));
        });
    },

    load_more_messages: function () {
        var self = this;
        var top_msg_id = this.$('.o_thread_message').first().data('messageId');
        var top_msg_selector = '.o_thread_message[data-message-id="' + top_msg_id + '"]';
        var offset = -framework.getPosition(document.querySelector(top_msg_selector)).top;
        this.fetch_and_render_thread(this.msg_ids, {force_fetch: true}).then(function(){
            offset += framework.getPosition(document.querySelector(top_msg_selector)).top;
            self.thread.scroll_to({offset: offset});
        });
    },

    /**
     * The value of the field has change (modification or switch to next document). Form view is
     * not re-rendered, simply updated. A re-fetch is needed.
     * @override
     */
    render_value: function () {
        return this.ready.then(this._render_value.bind(this));
    },

    _render_value: function () {
        // update context
        var context = _.extend(this.options.context || {},
            pyeval.eval('contexts', this.build_context())
        );
        this.context = _.extend({
            default_res_id: this.view.datarecord.id || false,
            default_model: this.view.model || false,
        }, context);
        this.thread_dataset = this.view.dataset;
        this.res_id = this.view.datarecord.id;
        this.record_name = this.view.datarecord.display_name;
        this.msg_ids = this.get_value() || [];

        // destroy current composer, if any
        if (this.composer) {
            this.composer.destroy();
            this.composer = undefined;
            this.mute_new_message_button(false);
        }

        // fetch and render messages of current document
        return this.fetch_and_render_thread(this.msg_ids);
    },
    refresh_followers: function () {
        if (this.followers) {
            this.followers.read_value();
        }
    },

    on_activity_schedule: function (event) {
        if (this.activities) {
            this.activities.on_activity_schedule(event);
        }
    },

    // composer toggle
    on_open_composer_new_message: function () {
        this.open_composer();
    },
    on_open_composer_log_note: function () {
        this.open_composer({is_log: true});
    },
    open_composer: function (options) {
        var self = this;
        var old_composer = this.composer;
        // create the new composer
        this.composer = new ChatterComposer(this, this.thread_dataset, {
            commands_enabled: false,
            context: this.context,
            input_min_height: 50,
            input_max_height: Number.MAX_VALUE, // no max_height limit for the chatter
            input_baseline: 14,
            is_log: options && options.is_log,
            record_name: this.record_name,
            default_body: old_composer && old_composer.$input && old_composer.$input.val(),
            default_mention_selections: old_composer && old_composer.mention_get_listener_selections(),
        });
        this.composer.on('input_focused', this, function () {
            this.composer.mention_set_prefetched_partners(this.mention_suggestions || []);
        });
        this.composer.insertAfter(this.$('.o_chatter_topbar')).then(function () {
            // destroy existing composer
            if (old_composer) {
                old_composer.destroy();
            }
            if (!config.device.touch) {
                self.composer.focus();
            }
            self.composer.on('post_message', self, self.on_post_message);
            self.composer.on('need_refresh', self, self.refresh_followers);
            self.composer.on('close_composer', null, self.close_composer.bind(self, true));
        });
        this.mute_new_message_button(true);
    },
    close_composer: function (force) {
        if (this.composer && (this.composer.is_empty() || force)) {
            this.composer.do_hide();
            this.composer.clear_composer();
            this.mute_new_message_button(false);
        }
    },
    mute_new_message_button: function (mute) {
        if (mute) {
            this.$('.o_chatter_button_new_message').removeClass('btn-primary').addClass('btn-default');
        } else if (!mute) {
            this.$('.o_chatter_button_new_message').removeClass('btn-default').addClass('btn-primary');
        }
    },

    destroy: function () {
        chat_manager.remove_chatter_messages(this.model);
        this._super.apply(this, arguments);
    },

});

core.form_widget_registry.add('mail_thread', Chatter);

return Chatter;

});
