odoo.define('mail.Chatter', function (require) {
"use strict";

var chat_manager = require('mail.chat_manager');
var composer = require('mail.composer');
var ChatThread = require('mail.ChatThread');

var ajax = require('web.ajax');
var config = require('web.config');
var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var form_common = require('web.form_common');
var session = require('web.session');

var _t = core._t;
var qweb = core.qweb;

// -----------------------------------------------------------------------------
// Followers Widget ('mail_followers' widget)
//
// Since it is displayed on a form view, it extends 'AbstractField' widget.
//
// Note: the followers widget is moved inside the chatter by the chatter itself
// for layout purposes.
// -----------------------------------------------------------------------------
var Followers = form_common.AbstractField.extend({
    template: 'mail.Followers',

    init: function () {
        this._super.apply(this, arguments);

        this.image = this.node.attrs.image || 'image_small';
        this.comment = this.node.attrs.help || false;
        this.ds_model = new data.DataSetSearch(this, this.view.model);
        this.ds_users = new data.DataSetSearch(this, 'res.users');

        this.value = [];
        this.followers = [];
        this.followers_fetched = $.Deferred();
        this.data_subtype = {};

        this.view_is_editable = this.__parentedParent.is_action_enabled('edit');
    },

    start: function () {
        // use actual_mode property on view to know if the view is in create mode anymore
        this.view.on("change:actual_mode", this, this.on_check_visibility_mode);
        this.on_check_visibility_mode();
        this.reinit();
        this.bind_events();
        return this._super();
    },

    on_check_visibility_mode: function () {
        this.set({"force_invisible": this.view.get("actual_mode") === "create"});
    },

    set_value: function (_value) {
        this.value = _value;
        this._super(_value);
    },

    reinit: function () {
        this.data_subtype = {};
        this.message_is_follower = undefined;
        this.display_buttons();
    },

    bind_events: function () {
        var self = this;

        // event: click on '(Un)Follow' button, that toggles the follow for uid
        this.$el.on('click', '.o_followers_follow_button', function () {
            if ($(this).hasClass('o_followers_notfollow')) {
                self.do_follow();
            } else {
                self.do_unfollow({user_ids: [session.uid]});
            }
        });

        // event: click on a subtype, that (un)subscribe for this subtype
        this.$el.on('click', '.o_subtypes_list input', function(event) {
            event.stopPropagation();
            self.do_update_subscription(event);
            var $list = self.$('.o_subtypes_list');
            if (!$list.hasClass('open')) {
                $list.addClass('open');
            }
            if (self.$('.o_subtypes_list ul')[0].children.length < 1) {
                $list.removeClass('open');
            }
        });

        // event: click on 'invite' button, that opens the invite wizard
        this.$el.on('click', '.o_add_follower', function(event) {
            event.preventDefault();
            self.on_invite_follower(false);
        });
        this.$el.on('click', '.o_add_follower_channel', function(event) {
            event.preventDefault();
            self.on_invite_follower(true);
        });

        // event: click on 'edit_subtype(pencil)' button to edit subscription
        this.$el.on('click', '.o_edit_subtype', self.on_edit_subtype);
        this.$el.on('click', '.o_remove_follower', self.on_remove_follower);
        this.$el.on('click', '.o_mail_redirect', self.on_click_redirect);
    },

    on_edit_subtype: function (event) {
        var self = this;
        var $currentTarget = $(event.currentTarget);
        var follower_id = $currentTarget.data('oe-id');
        var is_channel = $currentTarget.data('oe-model') === 'mail.channel';
        self.dialog = new Dialog(this, {
                        size: 'medium',
                        title: _t('Edit Subscription of ') + $currentTarget.siblings('a').text(),
                        buttons: [
                                {
                                    text: _t("Apply"),
                                    classes: 'btn-primary',
                                    click: function () {
                                        self.do_update_subscription(event, follower_id, is_channel);
                                    },
                                    close: true
                                },
                                {
                                    text: _t("Cancel"),
                                    close: true,
                                },
                            ],
                }).open();
        return self.fetch_subtypes($currentTarget.data('id'), $currentTarget.data('oe-model'));
    },

    on_invite_follower: function (channel_only) {
        var self = this;
        var action = {
            type: 'ir.actions.act_window',
            res_model: 'mail.wizard.invite',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            name: _t('Invite Follower'),
            target: 'new',
            context: {
                'default_res_model': this.view.dataset.model,
                'default_res_id': this.view.datarecord.id,
                'mail_invite_follower_channel_only': channel_only,
            },
        };
        this.do_action(action, {
            on_close: function () {
                self.read_value();
            },
        });
    },

    on_remove_follower: function (event) {
        var res_model = $(event.target).parent().find('a').data('oe-model');
        var res_id = $(event.target).parent().find('a').data('oe-id');
        if (res_model === 'res.partner') {
            return this.do_unfollow({partner_ids: [res_id]});
        } else {
            return this.do_unfollow({channel_ids: [res_id]});
        }
    },

    on_click_redirect: function (event) {
        event.preventDefault();
        var res_id = $(event.target).data('oe-id');
        var res_model = $(event.target).data('oe-model');
        this.trigger('redirect', res_model, res_id);
    },

    read_value: function () {
        var self = this;
        return this.ds_model.read_ids([this.view.datarecord.id], ['message_follower_ids'])
            .then(function (results) {
                self.value = results[0].message_follower_ids;
                self.render_value();
            });
    },

    render_value: function () {
        this.reinit();
        return this.fetch_followers(this.value);
    },

    fetch_followers: function (value_) {
        this.value = value_ || [];
        return ajax.jsonRpc('/mail/read_followers', 'call', {'follower_ids': this.value})
            .then(this.proxy('display_followers'), this.proxy('fetch_generic'))
            .then(this.proxy('display_buttons'))
            .then(this.proxy('fetch_subtypes'));
    },

    /** Read on res.partner failed: fall back on a generic case
        - fetch current user partner_id (call because no other smart solution currently) FIXME
        - then display a generic message about followers */
    fetch_generic: function () {
        var self = this;

        return this.ds_users.call('read', [[session.uid], ['partner_id']])
            .then(function (results) {
                var pid = results[0].partner_id[0];
                self.message_is_follower = (_.indexOf(self.value, pid) !== -1);
            })
            .then(self.proxy('display_generic'));
    },

    _format_followers: function (count){
        var str = '';
        if(count <= 0){
            str = _t('No follower');
        }else if(count === 1){
            str = _t('One follower');
        }else{
            str = ''+count+' '+_t('followers');
        }
        return str;
    },

    /* Display generic info about follower, for people not having access to res_partner */
    display_generic: function () {
        this.$('.o_followers_list').empty();
        this.$('.o_followers_count').html(this._format_followers(this.value.length));
    },

    /** Display the followers */
    display_followers: function (records) {
        var self = this;
        this.followers = records || this.followers;
        this.trigger('followers_update', this.followers);

        // clean and display title
        var $followers_list = this.$('.o_followers_list').empty();
        this.$('.o_followers_count').html(this._format_followers(this.followers.length));
        var user_follower = _.filter(this.followers, function (rec) { return rec.is_uid;});
        this.message_is_follower = user_follower.length >= 1;
        this.follower_id = this.message_is_follower ? user_follower[0].id : undefined;

        // render the dropdown content
        $(qweb.render('mail.Followers.add_more', {'widget': self})).appendTo($followers_list);
        var $follower_li;
        _(this.followers).each(function (record) {
            $follower_li = $(qweb.render('mail.Followers.partner', {
                'record': _.extend(record, {'avatar_url': '/web/image/' + record.res_model + '/' + record.res_id + '/image_small'}),
                'widget': self})
            );
            $follower_li.appendTo($followers_list);

            // On mouse-enter it will show the edit_subtype pencil.
            if (record.is_editable) {
                $follower_li.on('mouseenter mouseleave', function(e) {
                    $(e.currentTarget).find('.o_edit_subtype').toggleClass('hide', e.type === 'mouseleave');
                });
            }
        });
    },

    display_buttons: function () {
        if (this.message_is_follower) {
            this.$('button.o_followers_follow_button').removeClass('o_followers_notfollow').addClass('o_followers_following');
        } else {
            this.$('button.o_followers_follow_button').removeClass('o_followers_following').addClass('o_followers_notfollow');
        }
    },

    /** Fetch subtypes, only if current user is follower or if follower_id is given, i.e. if
     *  the current user is editing the subtypes of another follower
     *  @param {int} [follower_id] the id of the follower
     *  @param {string} [follower_model] 'res.partner' or 'mail.channel'
     */
    fetch_subtypes: function (follower_id, follower_model) {
        var self = this;
        var dialog = false;

        if (follower_id) {
            dialog = true;
        } else {
            this.$('.o_subtypes_list ul').empty();
            if (!this.message_is_follower) {
                this.$('.o_subtypes_list > .dropdown-toggle').attr('disabled', true);
                return;
            } else {
                this.$('.o_subtypes_list > .dropdown-toggle').attr('disabled', false);
            }
        }
        if (this.follower_id || follower_id) {
            return ajax.jsonRpc('/mail/read_subscription_data', 'call', {
                res_model: this.view.model,
                res_id: this.view.datarecord.id,
                follower_id: follower_id,
            }).then(function (data) {
                self.display_subtypes(data, dialog, (follower_model === 'mail.channel'));
            });
        } else  {
            return $.Deferred().resolve();
        }
    },

    /** Display subtypes: {'name': default, followed} */
    display_subtypes:function (data, dialog, display_warning) {
        var old_parent_model;
        var $list;
        if (dialog) {
            $list = $('<ul>').appendTo(this.dialog.$el);
        } else {
            $list = this.$('.o_subtypes_list ul');
        }
        $list.empty();

        this.data_subtype = data;
        this.records_length = _.map(data, function(value, index) { return index; }).length;

        if (this.records_length > 1) {
            this.display_followers();
        }

        _.each(data, function (record) {
            if (old_parent_model !== record.parent_model && old_parent_model !== undefined) {
                $list.append($('<li>').addClass('divider'));
            }
            old_parent_model = record.parent_model;
            record.followed = record.followed || undefined;
            $(qweb.render('mail.Followers.subtype', {'record': record,
                                                     'dialog': dialog,
                                                     'display_warning': display_warning && record.internal}))
            .appendTo($list);
        });

        if (display_warning) {
            $(qweb.render('mail.Followers.subtypes.warning')).appendTo(this.dialog.$el);
        }
    },

    do_follow: function () {
        var context = new data.CompoundContext(this.build_context(), {});
        this.$('.o_subtypes_list > .dropdown-toggle').attr('disabled', false);
        this.ds_model.call('message_subscribe_users', [[this.view.datarecord.id],
                                                       [session.uid],
                                                       undefined,
                                                       context])
            .then(this.proxy('read_value'));

        _.each(this.$('.o_subtypes_list input'), function (record) {
            $(record).attr('checked', 'checked');
        });
    },

    /**
     * Remove users, partners, or channels from the followers
     * @param {Array} [ids.user_ids] the user ids
     * @param {Array} [ids.partner_ids] the partner ids
     * @param {Array} [ids.channel_ids] the channel ids
     */
    do_unfollow: function (ids) {
        if (confirm(_t("Warning! \n If you remove a follower, he won't be notified of any email or discussion on this document. Do you really want to remove this follower ?"))) {
            _(this.$('.o_subtype_checkbox')).each(function (record) {
                $(record).attr('checked',false);
            });

            this.$('.o_subtypes_list > .dropdown-toggle').attr('disabled', true);
            var context = new data.CompoundContext(this.build_context(), {});

            if (ids.partner_ids || ids.channel_ids) {
                return this.ds_model.call(
                    'message_unsubscribe', [
                        [this.view.datarecord.id],
                        ids.partner_ids,
                        ids.channel_ids,
                        context]
                    ).then(this.proxy('read_value'));
            } else {
                return this.ds_model.call(
                    'message_unsubscribe_users', [
                        [this.view.datarecord.id],
                        ids.user_ids,
                        context]
                    ).then(this.proxy('read_value'));
            }
        }
        return false;
    },

    do_update_subscription: function (event, follower_id, is_channel) {
        var self = this;
        var kwargs = {};
        var ids = {};
        var action_subscribe;
        var subtypes;
        this.data_subtype = {};

        if (follower_id !== undefined) {
            // Subtypes edited from the modal
            action_subscribe = 'message_subscribe';
            subtypes = this.dialog.$('input[type="checkbox"]');
            if (is_channel) {
                ids.channel_ids = [follower_id];
            } else {
                ids.partner_ids = [follower_id];
            }
        } else {
            action_subscribe = 'message_subscribe_users';
            subtypes = this.$('.o_followers_actions input[type="checkbox"]');
            ids.user_ids = [session.uid];
        }
        kwargs = _.extend(kwargs, ids);

        // Get the subtype ids
        var checklist = [];
        _(subtypes).each(function (record) {
            if ($(record).is(':checked')) {
                checklist.push(parseInt($(record).data('id')));
            }
        });
        kwargs.subtype_ids = checklist;

        // If no more subtype followed, unsubscribe the follower
        if (!checklist.length) {
            if (!this.do_unfollow(ids)) {
                $(event.target).prop("checked", true);
            } else {
                self.$('.o_subtypes_list ul').empty();
            }
        } else {
            kwargs.context = new data.CompoundContext(this.build_context(), {});
            return this.ds_model._model.call(action_subscribe, [[this.view.datarecord.id]], kwargs).then(this.proxy('read_value'));
        }
    },
});

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
            internal_subtypes: [],
            default_body: '',
        });
        if (this.options.is_log) {
            this.options.send_text = _('Log');
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

    start: function () {
        var self = this;
        return this._super().then(function () {
            self.$input.val(self.options.default_body);
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
                subtype_id: false,
                subtype: 'mail.mt_comment',
                message_type: 'comment',
                content_subtype: 'html',
                context: self.context,
            });

            // Subtype
            if (self.options.is_log) {
                var subtype_id = parseInt(self.$('.o_chatter_composer_subtype_select').val());
                if (_.indexOf(_.pluck(self.options.internal_subtypes, 'id'), subtype_id) === -1) {
                    message.subtype = 'mail.mt_note';
                } else {
                    message.subtype_id = subtype_id;
                }
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
                    var parsed_email = parse_email(recipient[1]);
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
     * Check the additionnal partners (not necessary registered partners), and open a popup form view
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
                var parsed_email = parse_email(partner_name);

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
                dialog.view_form.on('on_button_cancel', self, function () {
                    names_to_remove.push(partner_name);
                    if (partner_id) {
                        recipient_ids_to_remove.push(partner_id);
                    }
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
                default_body: get_text2html(self.$input.val()),
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
            });
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
        "click .o_chatter_button_new_message": "on_open_composer_new_message",
        "click .o_chatter_button_log_note": "on_open_composer_log_note",
    },

    init: function () {
        this._super.apply(this, arguments);
        this.model = this.view.dataset.model;
        this.res_id = undefined;
        this.context = this.options.context || {};
    },

    willStart: function () {
        return chat_manager.is_ready;
    },

    start: function () {
        var self = this;

        // Move the follower's widget (if any) inside the chatter
        this.followers = this.field_manager.fields.message_follower_ids;
        if (this.followers) {
            this.$('.o_chatter_topbar').append(this.followers.$el);
            this.followers.on('redirect', this, this.on_redirect);
            this.followers.on('followers_update', this, this.on_followers_update);
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
        this.thread.on('redirect', this, this.on_redirect);
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

    fetch_and_render_thread: function (ids, options) {
        var self = this;
        options = options || {};
        options.ids = ids;
        return chat_manager.get_messages(options).then(function (raw_messages) {
            self.thread.render(raw_messages, {display_load_more: raw_messages.length < ids.length});
        });
    },

    on_post_message: function (message) {
        var self = this;
        var options = {model: this.model, res_id: this.res_id};
        chat_manager
            .post_message(message, options)
            .then(function () {
                self.close_composer();
                if (message.partner_ids.length) {
                    self.refresh_followers(); // refresh followers' list
                }
            })
            .fail(function () {
                // todo: display notification
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
            var discuss_ids = chat_manager.get_discuss_ids();
            self.do_action(discuss_ids.action_id, {active_id: channel_id});
        });
    },

    on_redirect: function (res_model, res_id) {
        this.do_action({
            type:'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            res_model: res_model,
            views: [[false, 'form']],
            res_id: res_id,
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
        this.fetch_and_render_thread(this.msg_ids, {force_fetch: true});
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
        this.context = _.extend({
            default_res_id: this.view.datarecord.id || false,
            default_model: this.view.model || false,
        }, this.options.context || {});
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
            context: this.context,
            input_min_height: 50,
            input_max_height: Number.MAX_VALUE, // no max_height limit for the chatter
            input_baseline: 14,
            internal_subtypes: this.options.internal_subtypes,
            is_log: options && options.is_log,
            record_name: this.record_name,
            default_body: old_composer && old_composer.$input.val(),
        });
        this.composer.on('input_focused', this, function () {
            this.composer.mention_set_prefetched_partners(this.mention_suggestions || []);
        });
        this.composer.insertBefore(this.$('.o_mail_thread')).then(function () {
            // destroy existing composer
            if (old_composer) {
                old_composer.destroy();
            }
            if (!config.device.touch) {
                self.composer.focus();
            }
            self.composer.on('post_message', self, self.on_post_message);
            self.composer.on('need_refresh', self, self.refresh_followers);
        });
        this.mute_new_message_button(true);
    },
    close_composer: function () {
        if (this.composer.is_empty()) {
            this.composer.do_hide();
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

// -----------------------------------------------------------------------------
// Utils
// -----------------------------------------------------------------------------
/**
 * Parses text to find email: Tagada <address@mail.fr> -> [Tagada, address@mail.fr] or False
 */
var parse_email = function (text) {
    var result = text.match(/(.*)<(.*@.*)>/);
    if (result) {
        return [_.str.trim(result[1]), _.str.trim(result[2])];
    }
    result = text.match(/(.*@.*)/);
    if (result) {
        return [_.str.trim(result[1]), _.str.trim(result[1])];
    }
    return [text, false];
};
/**
 * Replaces textarea text into html text (add <p>, <a>)
 * TDE note : should be done server-side, in Python -> use mail.compose.message ?
 */
var get_text2html = function (text) {
    return text
        .replace(/((?:https?|ftp):\/\/[\S]+)/g,'<a href="$1">$1</a> ')
        .replace(/[\n\r]/g,'<br/>');
};

core.form_widget_registry.add('mail_followers', Followers);
core.form_widget_registry.add('mail_thread', Chatter);

return Chatter;

});
