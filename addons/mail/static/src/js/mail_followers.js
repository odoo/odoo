odoo.define('mail.mail_followers', function (require) {
"use strict";

var ajax = require('web.ajax');
var mail_utils = require('mail.utils');
var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var form_common = require('web.form_common');
var session = require('web.session');
var web_client = require('web.web_client');

var _t = core._t;
var qweb = core.qweb;

/**
 * ------------------------------------------------------------
 * Mail Followers Widget
 * ------------------------------------------------------------
 *
 * This widget handles the display of a list of records as a vertical
 * list, with an image on the left. The widget itself is a floatting
 * right-sided box.
 * This widget is mainly used to display the followers of records
 * in OpenChatter.
 */


var Followers = form_common.AbstractField.extend({
    template: 'mail.Followers',

    init: function() {
        this._super.apply(this, arguments);

        this.image = this.node.attrs.image || 'image_small';
        this.comment = this.node.attrs.help || false;
        this.ds_model = new data.DataSetSearch(this, this.view.model);
        this.ds_users = new data.DataSetSearch(this, 'res.users');

        this.value = [];
        this.followers = [];
        this.data_subtype = {};

        this.view_is_editable = this.__parentedParent.is_action_enabled('edit');
    },

    start: function() {
        // use actual_mode property on view to know if the view is in create mode anymore
        this.view.on("change:actual_mode", this, this.on_check_visibility_mode);
        this.on_check_visibility_mode();
        this.reinit();
        this.bind_events();
        return this._super();
    },

    on_check_visibility_mode: function () {
        this.set({"force_invisible": this.view.get("actual_mode") == "create"});
    },

    set_value: function(_value) {
        this.value = _value;
        this._super(_value);
    },

    reinit: function() {
        this.data_subtype = {};
        this.message_is_follower = undefined;
        this.display_buttons();
    },

    bind_events: function() {
        var self = this;

        // event: click on '(Un)Follow' button, that toggles the follow for uid
        this.$('.o_timeline_follower').on('click', function () {
            if($(this).hasClass('o_timeline_notfollow')) {
                self.do_follow();
            }
            else {
                self.do_unfollow([session.uid]);
            }
        });

        // event: click on a subtype, that (un)subscribe for this subtype
        this.$el.on('click', '.o_timeline_subtype_list input', function(event) {
            self.do_update_subscription(event);
            var $list = self.$('.o_timeline_subtype_list');
            if(!$list.hasClass('open')) {
                $list.addClass('open');
            }
            if(self.$('.o_timeline_subtype_list ul')[0].children.length < 1) {
                $list.removeClass('open');
            }
            event.stopPropagation();
        });

        // event: click on 'invite' button, that opens the invite wizard
        this.$el.on('click', '.oe_invite', self.on_invite_follower);

        // event: click on 'edit_subtype(pencil)' button to edit subscription
        this.$el.on('click', '.oe_edit_subtype', self.on_edit_subtype);
        this.$el.on('click', '.oe_remove_follower', self.on_remove_follower);
        this.$el.on('click', 'a[data-partner]', self.on_follower_clicked);
    },

    on_edit_subtype: function(event) {
        var self = this;
        var $currentTarget = $(event.currentTarget);
        var user_pid = $currentTarget.data('id');
        $('div.oe_edit_actions').remove();
        self.$dialog = new Dialog(this, {
                        size: 'small',
                        title: _t('Edit Subscription of ') + $currentTarget.siblings('a').text(),
                        buttons: [
                                { text: _t("Apply"), click: function() {
                                    self.do_update_subscription(event, user_pid);
                                    this.parents('.modal').modal('hide');
                                }},
                                { text: _t("Cancel"), click: function() { this.parents('.modal').modal('hide'); }}
                            ],
                }, "<div class='oe_edit_actions'>").open();
        return self.fetch_subtypes(user_pid);
    },

    on_invite_follower: function () {
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
            },
        };
        this.do_action(action, {
            on_close: function() {
                self.read_value();
            },
        });
    },

    on_remove_follower: function (event) {
        var res_model = $(event.target).parent().find('a').data('res-model');
        var res_id = $(event.target).parent().find('a').data('res-id');
        if (res_model == 'res.partner') { return this.do_unfollow(undefined, [res_id], undefined); }
        else { return this.do_unfollow(undefined, undefined, [res_id]); }
    },

    on_follower_clicked: function  (event) {
        event.preventDefault();
        var partner_id = $(event.target).data('partner');
        var state = {
            'model': 'res.partner',
            'id': partner_id,
            'title': this.record_name
        };
        web_client.action_manager.do_push_state(state);
        var action = {
            type:'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            res_model: 'res.partner',
            views: [[false, 'form']],
            res_id: partner_id,
        };
        this.do_action(action);
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
                var pid = results[0]['partner_id'][0];
                self.message_is_follower = (_.indexOf(self.value, pid) != -1);
            })
            .then(self.proxy('display_generic'));
    },

    _format_followers: function(count){
        var str = '';
        if(count <= 0){
            str = _t('No followers');
        }else if(count === 1){
            str = _t('One follower');
        }else{
            str = ''+count+' '+_t('followers');
        }
        return str;
    },

    /* Display generic info about follower, for people not having access to res_partner */
    display_generic: function () {
        this.$('.o_timeline_follower_list').empty();
        this.$('.o_timeline_follower_title').html(this._format_followers(this.value.length));
    },

    /** Display the followers */
    display_followers: function (records) {
        var self = this;
        this.followers = records || this.followers;

        // clean and display title
        var node_user_list = this.$('.o_timeline_follower_list').empty();
        this.$('.o_timeline_follower_title').html(this._format_followers(this.followers.length));
        var user_follower = _.filter(this.followers, function (rec) { return rec.is_uid;});
        this.message_is_follower = user_follower.length >= 1;
        this.follower_id = this.message_is_follower ? user_follower[0]['id'] : undefined;
        $(qweb.render('mail.Followers.add_more', {'widget': self})).appendTo(node_user_list);

        // truncate number of displayed followers
        _(this.followers).each(function (record) {
            $(qweb.render('mail.Followers.partner', {
                'record': _.extend(record, {'avatar_url': '/web/image/' + record.res_model + '/' + record.res_id + '/image_small'}),
                'widget': self})
            ).appendTo(node_user_list);
            // On mouse-enter it will show the edit_subtype pencil.
            if (record.is_editable) {
                self.$('.o_timeline_follower_list').on('mouseenter mouseleave', function(e) {
                    self.$('.o_timeline_edit_subtype')
                        .toggleClass('oe_hidden', e.type == 'mouseleave');
                    self.$('.o_timeline_follower_list').find('.oe_partner')
                        .toggleClass('oe_partner_name', e.type == 'mouseenter');
                });
            }
        });
    },

    display_buttons: function () {
        if (this.message_is_follower) {
            this.$('button.o_timeline_follower').removeClass('o_timeline_notfollow').addClass('o_timeline_following');
        }
        else {
            this.$('button.o_timeline_follower').removeClass('o_timeline_following').addClass('o_timeline_notfollow');
        }

        if (this.view.is_action_enabled('edit')) {
            this.$('span.oe_timeline_invite_wrapper').hide();
        }
        else {
            this.$('span.oe_timeline_invite_wrapper').show();
        }
    },

    /** Fetch subtypes, only if current user is follower */
    fetch_subtypes: function (user_pid) {
        var self = this;
        var dialog = false;

        if (user_pid) {
            dialog = true;
        }
        else {
            this.$('.o_timeline_subtype_list ul').empty();
            if (! this.message_is_follower) {
                this.$('.o_timeline_subtype_list > .dropdown-toggle').attr('disabled', true);
                return;
            }
            else {
                this.$('.o_timeline_subtype_list > .dropdown-toggle').attr('disabled', false);
            }
        }
        if (this.follower_id) {
            return ajax.jsonRpc('/mail/read_subscription_data', 'call', {'res_model': this.view.model, 'res_id': this.view.datarecord.id})
                .then(function (data) { self.display_subtypes(data, dialog); });
        } else  {
            return $.Deferred().resolve();
        }
    },

    /** Display subtypes: {'name': default, followed} */
    display_subtypes:function (data, dialog) {
        var self = this;
        var $list = this.$('.o_timeline_subtype_list ul');

        if (_.isEmpty(this.data_subtype)) {
            this.data_subtype = data;

            if (dialog) {
                $list = this.$dialog.$el;
            }

            var old_parent_model;
            this.records_length = $.map(data, function(value, index) { return index; }).length;

            if (this.records_length > 1) {
                self.display_followers();
            }

            _.each(data, function (record) {
                if (old_parent_model !== record.parent_model && old_parent_model !== undefined) {
                    var $last_separator = $list.find('.oe_subtype').last();
                    if ($last_separator) {
                        $last_separator.addClass('oe_subtype_border');
                    }
                }
                old_parent_model = record.parent_model;
                record.followed = record.followed || undefined;
                $(qweb.render('mail.Followers.subtype', {'record': record,
                                                         'dialog': dialog}))
                .appendTo($list);
            });
        }
    },

    do_follow: function () {
        var context = new data.CompoundContext(this.build_context(), {});
        this.$('.o_timeline_subtype_list > .dropdown-toggle').attr('disabled', false);
        this.ds_model.call('message_subscribe_users', [[this.view.datarecord.id],
                                                       [session.uid],
                                                       undefined,
                                                       context])
            .then(this.proxy('read_value'));

        _.each(this.$('.o_timeline_subtype_list input'), function (record) {
            $(record).attr('checked', 'checked');
        });
    },

    do_unfollow: function (user_ids, partner_ids, channel_ids) {
        if (confirm(_t("Warning! \n If you remove a follower, he won't be notified of any email or discussion on this document. Do you really want to remove this follower ?"))) {
            _(this.$('.o_timeline_msg_subtype_check')).each(function (record) {
                $(record).attr('checked',false);
            });

            this.$('.o_timeline_subtype_list > .dropdown-toggle').attr('disabled', true);
            var context = new data.CompoundContext(this.build_context(), {});

            if (partner_ids || channel_ids) {
                return this.ds_model.call(
                    'message_unsubscribe', [
                        [this.view.datarecord.id],
                        partner_ids,
                        channel_ids,
                        context]
                    ).then(this.proxy('read_value'));
            }
            else {
                return this.ds_model.call(
                    'message_unsubscribe_users', [
                        [this.view.datarecord.id],
                        user_ids,
                        context]
                    ).then(this.proxy('read_value'));
            }
        }
        return false;
    },

    do_update_subscription: function (event, user_pid) {
        var self = this;
        this.data_subtype = {};

        var action_subscribe = 'message_subscribe_users';
        var follower_ids = [session.uid];
        var oe_action = this.$('.oe_actions input[type="checkbox"]');

        if (user_pid) {
            action_subscribe = 'message_subscribe';
            follower_ids = [user_pid];
            oe_action = $('.oe_edit_actions input[type="checkbox"]');
        }

        var checklist = [];
        _(oe_action).each(function (record) {
            if ($(record).is(':checked')) {
                checklist.push(parseInt($(record).data('id')));
            }
        });

        if (!checklist.length) {
            if (!this.do_unfollow(undefined, [user_pid], undefined)) {
                $(event.target).attr("checked", "checked");
            }
            else {
                  self.$('.o_timeline_subtype_list ul').empty();
            }
        }
        else {
            var context = new data.CompoundContext(this.build_context(), {});
            return this.ds_model.call(action_subscribe, [[this.view.datarecord.id], follower_ids, undefined, checklist, context])
                .then(this.proxy('read_value'));
        }
    },
});

/* Add the widget to registry */
core.form_widget_registry.add('mail_followers', Followers);

});
