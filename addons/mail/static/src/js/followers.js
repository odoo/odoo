odoo.define('mail.Followers', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var concurrency = require('web.concurrency');
var core = require('web.core');
var Dialog = require('web.Dialog');
var field_registry = require('web.field_registry');
var session = require('web.session');

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
        'click .o_subtypes_list .custom-checkbox': '_onSubtypeClicked',
        // click on 'invite' button, that opens the invite wizard
        'click .o_add_follower': '_onAddFollower',
        'click .o_add_follower_channel': '_onAddChannel',
        // click on 'edit_subtype' (pencil) button to edit subscription
        'click .o_edit_subtype': '_onEditSubtype',
        'click .o_remove_follower': '_onRemoveFollower',
        'click .o_mail_redirect': '_onRedirect',
    },
    // this widget only supports one2many but is not generic enough to claim
    // that it supports all one2many fields
    // supportedFieldTypes: ['one2many'],

    // inherited
    init: function (parent, name, record, options) {
        this._super.apply(this, arguments);

        this.image = this.attrs.image || 'image_128';
        this.comment = this.attrs.help || false;

        this.followers = [];
        this.subtypes = [];
        this.data_subtype = {};
        this._isFollower = undefined;
        this.partnerID = session.partner_id;

        this.dp = new concurrency.DropPrevious();

        options = options || {};
        this.isEditable = options.isEditable;
    },
    _render: function () {
        // note: the rendering of this widget is asynchronous as it needs to
        // fetch the details of the followers, but it performs a first rendering
        // synchronously (_displayGeneric), and updates its rendering once it
        // has fetched the required data, so this function doesn't return a promise
        // as we don't want to wait to the data to be loaded to display the widget
        var self = this;
        var fetch_def = this.dp.add(this._readFollowers());

        concurrency.rejectAfter(concurrency.delay(0), fetch_def).then(this._displayGeneric.bind(this));

        return fetch_def.then(function () {
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
        if (this._isFollower) {
            this.$('button.o_followers_follow_button').removeClass('o_followers_notfollow').addClass('o_followers_following');
            this.$('.o_subtypes_list > .dropdown-toggle').attr('disabled', false);
            this.$('.o_followers_actions .dropdown-toggle').addClass('o_followers_following');
        } else {
            this.$('button.o_followers_follow_button').removeClass('o_followers_following').addClass('o_followers_notfollow');
            this.$('.o_subtypes_list > .dropdown-toggle').attr('disabled', true);
            this.$('.o_followers_actions .dropdown-toggle').removeClass('o_followers_following');
        }
        this.$('button.o_followers_follow_button').attr("aria-pressed", this.is_follower);
    },
    _displayGeneric: function () {
        // only display the number of followers (e.g. if read failed)
        this.$('.o_followers_actions').hide();
        this.$('.o_followers_title_box > button').prop('disabled', true);
        this.$('.o_followers_count')
            .html(this.value.res_ids.length)
            .parent().attr('title', this._formatFollowers(this.value.res_ids.length));
    },
    _displayFollowers: function () {
        var self = this;

        // render the dropdown content
        var $followers_list = this.$('.o_followers_list').empty();
        $(QWeb.render('mail.Followers.add_more', {widget: this})).appendTo($followers_list);
        var $follower_li;
        _.each(this.followers, function (record) {
            if (!record.is_active) {
                record.title = _.str.sprintf(_t('%s \n(inactive)'), record.name);
            } else {
                record.title = record.name;
            }

            $follower_li = $(QWeb.render('mail.Followers.partner', {
                'record': record,
                'widget': self})
            );
            $follower_li.appendTo($followers_list);

            // On mouse-enter it will show the edit_subtype pencil.
            if (record.is_editable) {
                $follower_li.on('mouseenter mouseleave', function (e) {
                    $(e.currentTarget).find('.o_edit_subtype').toggleClass('d-none', e.type === 'mouseleave');
                });
            }
        });

        // clean and display title
        this.$('.o_followers_actions').show();
        this.$('.o_followers_title_box > button').prop('disabled', !$followers_list.children().length);
        this.$('.o_followers_count')
            .html(this.value.res_ids.length)
            .parent().attr('title', this._formatFollowers(this.value.res_ids.length));
    },
    _displaySubtypes:function (data, dialog, display_warning) {
        var old_parent_model;
        var $list;
        if (dialog) {
            $list = $('<div>').appendTo(this.dialog.$el);
        } else {
            $list = this.$('.o_subtypes_list .dropdown-menu');
        }
        $list.empty();

        this.data_subtype = data;

        _.each(data, function (record) {
            if (old_parent_model !== record.parent_model && old_parent_model !== undefined) {
                $list.append($('<div>', {class: 'dropdown-divider'}));
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
            views: [[false, 'form']],
            name: _t("Invite Follower"),
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
            str = _t("No follower");
        } else if (count === 1){
            str = _t("One follower");
        } else {
            str = ''+count+' '+_t("followers");
        }
        return str;
    },
    _readFollowers: function () {
        var missing_ids = _.difference(this.value.res_ids, _.pluck(this.followers, 'id'));
        var def;
        if (missing_ids.length) {
            def = this._rpc({
                    route: '/mail/read_followers',
                    params: { follower_ids: missing_ids, context: {} } // empty context to be overridden in session.js with 'allowed_company_ids'
                });
        }
        return Promise.resolve(def).then((results) => {
            if (results) {
                // Preprocess records
                _.each(results.followers, (record) => {
                    var resModel = record.partner_id ? 'res.partner' : 'mail.channel';
                    var resId = record.partner_id ? record.partner_id : record.channel_id;
                    record.res_id = resId;
                    record.res_model = resModel;
                    record.avatar_url = '/web/image/' + resModel + '/' + resId + '/image_128';
                });
                this.followers = _.uniq(results.followers.concat(this.followers), 'id');
                if (results.subtypes) { //read_followers will return False if current user is not in the list
                    this.subtypes = results.subtypes;
                }
            }
            // filter out previously fetched followers that are no longer following
            this.followers = _.filter(this.followers, (follower) => {
                return _.contains(this.value.res_ids, follower.id);
            });
            var userFollower = _.filter(this.followers, (rec) => {
                return this.partnerID === rec.partner_id;
            });
            this._isFollower = userFollower.length >= 1;
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
        this._rpc({
                model: this.model,
                method: 'message_subscribe',
                args: [[this.res_id]],
                kwargs: kwargs,
            })
            .then(this._reload.bind(this));
    },
    /**
     * Remove partners or channels from the followers
     *
     * @private
     * @param {Object} ids
     * @param {Array} [ids.partner_ids] the partner ids
     * @param {Array} [ids.channel_ids] the channel ids
     */
    _messageUnsubscribe: function (ids) {
        return this._rpc({
            model: this.model,
            method: 'message_unsubscribe',
            args: [[this.res_id], ids.partner_ids, ids.channel_ids],
        }).then(this._reload.bind(this));
    },
    /**
     * Remove partners or channels from the followers
     * @param {Array} [ids.partner_ids] the partner ids
     * @param {Array} [ids.channel_ids] the channel ids
     */
    _unfollow: function (ids) {
        var self = this;
        // do not prompt confirmation dialog on unsubscribe of current user.
        if (_.isEqual(ids.partner_ids, [this.partnerID]) && _.isEmpty(ids.channel_ids)) {
            return this._messageUnsubscribe(ids);
        }
        return new Promise(function (resolve, reject) {
            var follower = _.find(self.followers, { res_id: ids.partner_ids ? ids.partner_ids[0] : ids.channel_ids[0] });
            var text = _.str.sprintf(_t("If you remove a follower, he won't be notified of any email or discussion on this document. Do you really want to remove %s?"), follower.name);
            Dialog.confirm(this, text, {
                title: _t("Warning"),
                confirm_callback: function () {
                    self._messageUnsubscribe(ids);
                    resolve();
                },
                cancel_callback: reject,
            });
        });
    },
    _updateSubscription: function (event, followerID, isChannel) {
        var ids = {};
        var subtypes;

        if (followerID !== undefined) {
            // Subtypes edited from the modal
            subtypes = this.dialog.$('input[type="checkbox"]');
            if (isChannel) {
                ids.channel_ids = [followerID];
            } else {
                ids.partner_ids = [followerID];
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
            this._unfollow(ids).guardedCatch(function () {
                $(event.currentTarget).find('input').addBack('input').prop('checked', true);
            });
        } else {
            var kwargs = _.extend({}, ids);
            if (followerID === undefined || followerID === this.partnerID) {
                //this.subtypes will only be updated if the current user
                //just added himself to the followers. We need to update
                //the subtypes manually when editing subtypes
                //for current user
                _.each(this.subtypes, function (subtype) {
                    subtype.followed = checklist.indexOf(subtype.id) > -1;
                });
            }
            kwargs.subtype_ids = checklist;
            kwargs.context = {}; // FIXME
            this._rpc({
                    model: this.model,
                    method: 'message_subscribe',
                    args: [[this.res_id]],
                    kwargs: kwargs,
                })
                .then(this._reload.bind(this));
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAddFollower: function (ev) {
        ev.preventDefault();
        this._inviteFollower(false);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAddChannel: function (ev) {
        ev.preventDefault();
        this._inviteFollower(true);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onEditSubtype: function (ev) {
        var self = this;
        var $currentTarget = $(ev.currentTarget);
        var follower_id = $currentTarget.data('follower-id'); // id of model mail_follower
        this._rpc({
                route: '/mail/read_subscription_data',
                params: {follower_id: follower_id},
            })
            .then(function (data) {
                var res_id = $currentTarget.data('oe-id'); // id of model res_partner or mail_channel
                var is_channel = $currentTarget.data('oe-model') === 'mail.channel';
                self.dialog = new Dialog(this, {
                    size: 'medium',
                    title: _t("Edit Subscription of ") + $currentTarget.siblings('a').text(),
                    buttons: [
                        {
                            text: _t("Apply"),
                            classes: 'btn-primary',
                            click: function () {
                                self._updateSubscription(ev, res_id, is_channel);
                            },
                            close: true
                        },
                        {
                            text: _t("Cancel"),
                            close: true,
                        },
                    ],
                });
                self.dialog.opened().then(function () {
                    self._displaySubtypes(data, true, is_channel);
                });
                self.dialog.open();
            });
    },
    /**
     * @private
     */
    _onFollowButtonClicked: function () {
        if (!this._isFollower) {
            this._follow();
        } else {
            this._unfollow({partner_ids: [this.partnerID]});
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onRedirect: function (ev) {
        ev.preventDefault();
        var $target = $(ev.target);
        this.do_action({
            type: 'ir.actions.act_window',
            view_mode: 'form',
            res_model: $target.data('oe-model'),
            views: [[false, 'form']],
            res_id: $target.data('oe-id'),
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onRemoveFollower: function (ev) {
        var resModel = $(ev.target).parent().find('a').data('oe-model');
        var resID = $(ev.target).parent().find('a').data('oe-id');
        if (resModel === 'res.partner') {
            return this._unfollow({partner_ids: [resID]});
        } else {
            return this._unfollow({channel_ids: [resID]});
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onSubtypeClicked: function (ev) {
        ev.stopPropagation();
        this._updateSubscription(ev);
        var $list = this.$('.o_subtypes_list');
        if (!$list.hasClass('show')) {
            $list.addClass('show');
        }
        if (this.$('.o_subtypes_list .dropdown-menu')[0].children.length < 1) {
            $list.removeClass('show');
        }
    },
});

field_registry.add('mail_followers', Followers);

return Followers;

});
