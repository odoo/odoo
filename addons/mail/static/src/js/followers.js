odoo.define('mail.Followers', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var concurrency = require('web.concurrency');
var core = require('web.core');
var Dialog = require('web.Dialog');
var field_registry = require('web.field_registry');

var _t = core._t;
var QWeb = core.qweb;

// -----------------------------------------------------------------------------
// Followers ('mail_followers') widget
// -----------------------------------------------------------------------------
var Followers = AbstractField.extend({
    template: 'mail.Followers',
    events: {
        // click on '(Un)Follow' button, that toggles the follow for uid
        'click .o_followers_follow_button': '_onFollowButtonClicked',
        // click on a subtype, that (un)subscribes for this subtype
        'click .o_subtypes_list input': '_onSubtypeClicked',
        // click on 'invite' button, that opens the invite wizard
        'click .o_add_follower': '_onAddFollower',
        'click .o_add_follower_channel': '_onAddChannel',
        // click on 'edit_subtype' (pencil) button to edit subscription
        'click .o_edit_subtype': '_onEditSubtype',
        'click .o_remove_follower': '_onRemoveFollower',
        'click .o_mail_redirect': '_onRedirect',
    },
    supportedFieldTypes: ['one2many'],

    // inherited
    init: function(parent, name, record, options) {
        this._super.apply(this, arguments);

        this.image = this.attrs.image || 'image_small';
        this.comment = this.attrs.help || false;

        this.followers = [];
        this.subtypes = [];
        this.data_subtype = {};
        this.is_follower = undefined;
        var session = this.getSession();
        this.partnerID = session.partner_id;

        this.dp = new concurrency.DropPrevious();

        options = options || {};
        this.isEditable = options.isEditable;
    },
    _render: function () {
        // note: the rendering of this widget is asynchronous as it needs to
        // fetch the details of the followers, but it performs a first rendering
        // synchronously (_displayGeneric), and updates its rendering once it
        // has fetched the required data, so this function doesn't return a deferred
        // as we don't want to wait to the data to be loaded to display the widget
        var self = this;
        var fetch_def = this.dp.add(this._readFollowers());

        concurrency.rejectAfter(concurrency.delay(0), fetch_def).then(this._displayGeneric.bind(this));

        fetch_def.then(function () {
            self._displayButtons();
            self._displayFollowers(self.followers);
            if (self.subtypes) { // current user is follower
                self._displaySubtypes(self.subtypes);
            }
        });
    },
    isSet: function () {
        return true;
    },
    _reset: function (record) {
        this._super.apply(this, arguments);
        // the mail widgets being persistent, one need to update the res_id on reset
        this.res_id = record.res_id;
    },

    // public
    getFollowers: function () {
        return this.followers;
    },

    // private
    _displayButtons: function () {
        if (this.is_follower) {
            this.$('button.o_followers_follow_button').removeClass('o_followers_notfollow').addClass('o_followers_following');
            this.$('.o_subtypes_list > .dropdown-toggle').attr('disabled', false);
            this.$('.o_followers_actions .dropdown-toggle').addClass('o_followers_following');
        } else {
            this.$('button.o_followers_follow_button').removeClass('o_followers_following').addClass('o_followers_notfollow');
            this.$('.o_subtypes_list > .dropdown-toggle').attr('disabled', true);
            this.$('.o_followers_actions .dropdown-toggle').removeClass('o_followers_following');
        }
    },
    _displayGeneric: function () {
        // only display the number of followers (e.g. if read failed)
        this.$('.o_followers_actions').hide();
        this.$('.o_followers_title_box > button').prop('disabled', true);
        this.$('.o_followers_count')
            .html(this.value.res_ids.length)
            .parent().attr("title", this._formatFollowers(this.value.res_ids.length));
    },
    _displayFollowers: function () {
        var self = this;

        // render the dropdown content
        var $followers_list = this.$('.o_followers_list').empty();
        $(QWeb.render('mail.Followers.add_more', {widget: this})).appendTo($followers_list);
        var $follower_li;
        _.each(this.followers, function (record) {
            $follower_li = $(QWeb.render('mail.Followers.partner', {
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

        // clean and display title
        this.$('.o_followers_actions').show();
        this.$('.o_followers_title_box > button').prop('disabled', !$followers_list.children().length);
        this.$('.o_followers_count')
            .html(this.value.res_ids.length)
            .parent().attr("title", this._formatFollowers(this.value.res_ids.length));
    },
    _displaySubtypes:function (data, dialog, display_warning) {
        var old_parent_model;
        var $list;
        if (dialog) {
            $list = $('<ul>').appendTo(this.dialog.$el);
        } else {
            $list = this.$('.o_subtypes_list ul');
        }
        $list.empty();

        this.data_subtype = data;

        _.each(data, function (record) {
            if (old_parent_model !== record.parent_model && old_parent_model !== undefined) {
                $list.append($('<li>').addClass('divider'));
            }
            old_parent_model = record.parent_model;
            record.followed = record.followed || undefined;
            $list.append(QWeb.render('mail.Followers.subtype', {
                'record': record,
                'dialog': dialog,
                'display_warning': display_warning && record.internal,
            }));
        });

        if (display_warning) {
            $(QWeb.render('mail.Followers.subtypes.warning')).appendTo(this.dialog.$el);
        }
    },
    _inviteFollower: function (channel_only) {
        var action = {
            type: 'ir.actions.act_window',
            res_model: 'mail.wizard.invite',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            name: _t('Invite Follower'),
            target: 'new',
            context: {
                'default_res_model': this.model,
                'default_res_id': this.res_id,
                'mail_invite_follower_channel_only': channel_only,
            },
        };
        this.do_action(action, {
            on_close: this._reload.bind(this),
        });
    },
    _formatFollowers: function (count){
        var str = '';
        if (count <= 0) {
            str = _t('No follower');
        } else if (count === 1){
            str = _t('One follower');
        } else {
            str = ''+count+' '+_t('followers');
        }
        return str;
    },
    _readFollowers: function () {
        var self = this;
        var missing_ids = _.difference(this.value.res_ids, _.pluck(this.followers, 'id'));
        var def;
        if (missing_ids.length) {
            var args = { follower_ids: missing_ids, res_model: this.model };
            def = this.performRPC('/mail/read_followers', args);
        }
        return $.when(def).then(function (results) {
            if (results) {
                self.followers = self.followers.concat(results.followers);
                self.subtypes = results.subtypes;
            }
            // filter out previously fetched followers that are no longer following
            self.followers = _.filter(self.followers, function (follower) {
                return _.contains(self.value.res_ids, follower.id);
            });
            var user_follower = _.filter(self.followers, function (rec) { return rec.is_uid; });
            self.is_follower = user_follower.length >= 1;
        });
    },
    _reload: function () {
        this.trigger_up('reload', {fieldNames: [this.name]});
    },
    _follow: function () {
        var kwargs = {
            partner_ids: [this.partnerID],
            context: {}, // FIXME
        };
        this.rpc(this.model, 'message_subscribe')
            .args([[this.res_id]])
            .kwargs(kwargs)
            .exec()
            .then(this._reload.bind(this));
    },
    /**
     * Remove partners or channels from the followers
     * @param {Array} [ids.partner_ids] the partner ids
     * @param {Array} [ids.channel_ids] the channel ids
     */
    _unfollow: function (ids) {
        var self = this;
        var def = $.Deferred();
        var text = _t("Warning! \n If you remove a follower, he won't be notified of any email or discussion on this document.\n Do you really want to remove this follower ?");
        Dialog.confirm(this, text, {
            confirm_callback: function () {
                var args = [
                    [self.res_id],
                    ids.partner_ids,
                    ids.channel_ids,
                    {}, // FIXME
                ];
                self.rpc(self.model, 'message_unsubscribe')
                    .args(args)
                    .exec()
                    .then(self._reload.bind(self));
                def.resolve();
            },
            cancel_callback: def.reject.bind(def),
        });
        return def;
    },
    _updateSubscription: function (event, follower_id, is_channel) {
        var ids = {};
        var subtypes;

        if (follower_id !== undefined) {
            // Subtypes edited from the modal
            subtypes = this.dialog.$('input[type="checkbox"]');
            if (is_channel) {
                ids.channel_ids = [follower_id];
            } else {
                ids.partner_ids = [follower_id];
            }
        } else {
            subtypes = this.$('.o_followers_actions input[type="checkbox"]');
            ids.partner_ids = [this.partnerID];
        }

        // Get the subtype ids
        var checklist = [];
        _.each(subtypes, function (record) {
            if ($(record).is(':checked')) {
                checklist.push(parseInt($(record).data('id')));
            }
        });

        // If no more subtype followed, unsubscribe the follower
        if (!checklist.length) {
            this._unfollow(ids).fail(function () {
                $(event.target).prop("checked", true);
            });
        } else {
            var kwargs = _.extend({}, ids);
            kwargs.subtype_ids = checklist;
            kwargs.context = {}; // FIXME
            this.rpc(this.model, 'message_subscribe')
                .args([[this.res_id]])
                .kwargs(kwargs)
                .exec()
                .then(this._reload.bind(this));
        }
    },

    // handlers
    _onAddFollower: function (event) {
        event.preventDefault();
        this._inviteFollower(false);
    },
    _onAddChannel: function (event) {
        event.preventDefault();
        this._inviteFollower(true);
    },
    _onEditSubtype: function (event) {
        var self = this;
        var $currentTarget = $(event.currentTarget);
        var follower_id = $currentTarget.data('follower-id'); // id of model mail_follower
        return this.performRPC('/mail/read_subscription_data', {
            res_model: this.model,
            follower_id: follower_id,
        }).then(function (data) {
            var res_id = $currentTarget.data('oe-id'); // id of model res_partner or mail_channel
            var is_channel = $currentTarget.data('oe-model') === 'mail.channel';
            self.dialog = new Dialog(this, {
                size: 'medium',
                title: _t('Edit Subscription of ') + $currentTarget.siblings('a').text(),
                buttons: [
                    {
                        text: _t("Apply"),
                        classes: 'btn-primary',
                        click: function () {
                            self._updateSubscription(event, res_id, is_channel);
                        },
                        close: true
                    },
                    {
                        text: _t("Cancel"),
                        close: true,
                    },
                ],
            }).open();
            self._displaySubtypes(data, true, is_channel);
        });
    },
    _onFollowButtonClicked: function () {
        if (!this.is_follower) {
            this._follow();
        } else {
            this._unfollow({partner_ids: [this.partnerID]});
        }
    },
    _onRedirect: function (event) {
        event.preventDefault();
        var $target = $(event.target);
        this.do_action({
            type: 'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            res_model: $target.data('oe-model'),
            views: [[false, 'form']],
            res_id: $target.data('oe-id'),
        });
    },
    _onRemoveFollower: function (event) {
        var res_model = $(event.target).parent().find('a').data('oe-model');
        var res_id = $(event.target).parent().find('a').data('oe-id');
        if (res_model === 'res.partner') {
            return this._unfollow({partner_ids: [res_id]});
        } else {
            return this._unfollow({channel_ids: [res_id]});
        }
    },
    _onSubtypeClicked: function (event) {
        event.stopPropagation();
        this._updateSubscription(event);
        var $list = this.$('.o_subtypes_list');
        if (!$list.hasClass('open')) {
            $list.addClass('open');
        }
        if (this.$('.o_subtypes_list ul')[0].children.length < 1) {
            $list.removeClass('open');
        }
    },
});

field_registry.add('mail_followers', Followers);

return Followers;

});
