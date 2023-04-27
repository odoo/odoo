odoo.define('base_setup.ResConfigInviteUsers', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var widget_registry = require('web.widget_registry');
    var core = require('web.core');

    var _t = core._t;

    var ResConfigInviteUsers = Widget.extend({
        template: 'res_config_invite_users',

        events: {
            'click .o_web_settings_invite': '_onClickInvite',
            'click .o_web_settings_user': '_onClickUser',
            'click .o_web_settings_more': '_onClickMore',
            'keydown .o_user_emails': '_onKeydownUserEmails',
        },

        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.emails = [];
        },

        willStart: function () {
            var self = this;

            return this._super.apply(this, arguments).then(function () {
                return self.load();
            });
        },

        load: function () {
            var self = this;

            return this._rpc({
                route: '/base_setup/data',
            }).then(function (data) {
                self.active_users = data.active_users;
                self.pending_users = data.pending_users;
                self.pending_count = data.pending_count;
                self.resend_invitation = data.resend_invitation || false;
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {string} email
         * @returns {boolean} true if the given email address is valid
         */
        _validateEmail: function (email) {
            var re = /^([a-z0-9][-a-z0-9_\+\.]*)@((?:[\w-]+\.)*\w[\w-]{0,66})\.([a-z]{2,63}(?:\.[a-z]{2})?)$/i;
            return re.test(email);
        },

        /**
         * Send invitation for valid and unique email addresses
         *
         * @private
         */
        _invite: function () {
            var self = this;

            var $userEmails = this.$('.o_user_emails');
            $userEmails.prop('disabled', true);
            this.$('.o_web_settings_invite').prop('disabled', true);
            var value = $userEmails.val().trim();
            if (value) {
                // filter out duplicates
                var emails = _.uniq(value.split(/[ ,;\n]+/));

                // filter out invalid email addresses
                var invalidEmails = _.reject(emails, this._validateEmail);
                if (invalidEmails.length) {
                    this.do_warn(false, _.str.sprintf(
                        _t('Invalid email addresses: %s.'),
                        invalidEmails.join(', ')
                    ));
                }
                emails = _.difference(emails, invalidEmails);

                if (!this.resend_invitation) {
                    // filter out already processed or pending addresses
                    var pendingEmails = _.map(this.pending_users, function (info) {
                        return info[1];
                    });
                    var existingEmails = _.intersection(emails, this.emails.concat(pendingEmails));
                    if (existingEmails.length) {
                        this.do_warn(false, _.str.sprintf(
                            _t('Email addresses already existing: %s.'),
                            existingEmails.join(', ')
                        ));
                    }
                    emails = _.difference(emails, existingEmails);
                }

                if (emails.length) {
                    $userEmails.val('');
                    this._rpc({
                        model: 'res.users',
                        method: 'web_create_users',
                        args: [emails],
                    }).then(function () {
                        return self.load().then(function () {
                            self.renderElement();
                            self.$('.o_user_emails').focus();
                        });
                    });
                } else {
                    $userEmails.prop('disabled', false);
                    this.$('.o_web_settings_invite').prop('disabled', false);
                    self.$('.o_user_emails').focus();
                }
            }
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickInvite: function (ev) {
            if (this.$('.o_user_emails').val().length) {
                var $button = $(ev.target);
                $button.button('loading');
                return this._invite();
            }
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickMore: function (ev) {
            var self = this;
            ev.preventDefault();
            this._rpc({
                model: 'ir.model.data',
                method: 'xmlid_to_res_model_res_id',
                args: ["base.view_users_form"],
            })
            .then(function (data) {
                self.do_action({
                    name: _t('Users'),
                    type: 'ir.actions.act_window',
                    view_mode: 'tree,form',
                    res_model: 'res.users',
                    domain: [['log_ids', '=', false]],
                    context: {
                        search_default_no_share: true,
                    },
                    views: [[false, 'list'], [data[1], 'form']],
                });
            });
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickUser: function (ev) {
            var self = this;
            ev.preventDefault();
            var user_id = $(ev.currentTarget).data('user-id');
            this._rpc({
                model: 'ir.model.data',
                method: 'xmlid_to_res_model_res_id',
                args: ["base.view_users_form"],
            })
            .then(function (data) {
                self.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'res.users',
                    view_mode: 'form',
                    res_id: user_id,
                    views: [[data[1], 'form']],
                });
            });
        },
        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onKeydownUserEmails: function (ev) {
            var keyCodes = [$.ui.keyCode.TAB, $.ui.keyCode.COMMA, $.ui.keyCode.ENTER];
            if (_.contains(keyCodes, ev.which)) {
                ev.preventDefault();
                this._invite();
            }
        },
    });

   widget_registry.add('res_config_invite_users', ResConfigInviteUsers);

});
