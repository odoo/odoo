odoo.define('base_setup.ResConfigInviteUsers', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var widget_registry = require('web.widget_registry');
    var core = require('web.core');
    var framework = require('web.framework');

    var QWeb = core.qweb;
    var _t = core._t;

    var ResConfigInviteUsers = Widget.extend({
        template: 'res_config_invite_users',

        events: {
            'click .o_web_settings_invite': '_onClickInvite',
            'click .o_web_settings_access_rights': '_onClickAccessRights',
            'click .o_web_settings_user': '_onClickUser',
            'click .o_web_settings_more': '_onClickMore',
            'click .o_badge_remove': '_onClickBadgeRemove',
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
         * Creates and appends badges for valid and unique email addresses
         *
         * @private
         */
        _createBadges: function () {
            var $userEmails = this.$('.o_user_emails');
            var value = $userEmails.val().trim();
            if (value) {
                // filter out duplicates
                var emails = _.uniq(value.split(/[ ,;\n]+/));

                // filter out invalid email addresses
                var invalidEmails = _.reject(emails, this._validateEmail);
                if (invalidEmails.length) {
                    this.do_warn(_.str.sprintf(_t('The following email addresses are invalid: %s.'), invalidEmails.join(', ')));
                }
                emails = _.difference(emails, invalidEmails);

                if (!this.resend_invitation) {
                    // filter out already processed or pending addresses
                    var pendingEmails = _.map(this.pending_users, function (info) {
                        return info[1];
                    });
                    var existingEmails = _.intersection(emails, this.emails.concat(pendingEmails));
                    if (existingEmails.length) {
                        this.do_warn(_.str.sprintf(_t('The following email addresses already exist: %s.'), existingEmails.join(', ')));
                    }
                    emails = _.difference(emails, existingEmails);
                }

                // add valid email addresses, if any
                if (emails.length) {
                    this.emails = this.emails.concat(emails);
                    this.$('.o_web_settings_invitation_form').append(QWeb.render('EmailBadge', {emails: emails}));
                    $userEmails.val('');
                }
            }
        },
        /**
         * Removes a given badge from the DOM, and its associated email address
         *
         * @private
         * @param {jQueryElement} $badge
         */
        _removeBadge: function ($badge) {
            var email = $badge.text().trim();
            this.emails = _.without(this.emails, email);
            $badge.remove();
        },
        /**
         * @private
         * @param {string} email
         * @returns {boolean} true if the given email address is valid
         */
        _validateEmail: function (email) {
            var re = /^([a-z0-9][-a-z0-9_\+\.]*)@((?:[\w-]+\.)*\w[\w-]{0,66})\.([a-z]{2,63}(?:\.[a-z]{2})?)$/i;
            return re.test(email);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickAccessRights: function (e) {
            e.preventDefault();
            this.do_action('base.action_res_users');
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickBadgeRemove: function (ev) {
            var $badge = $(ev.target).closest('.badge');
            this._removeBadge($badge);
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickInvite: function (ev) {
            var self = this;
            this._createBadges();
            if (this.emails.length) {
                var $button = $(ev.target);
                $button.button('loading');
                this._rpc({
                    model: 'res.users',
                    method: 'web_create_users',
                    args: [this.emails],
                }).then(function () {
                    return self.load().then(function () {
                        self.renderElement();
                    });
                }).guardedCatch(function () {
                    // NOTE Not sure that this is needed
                    $button.button('reset');
                });
            }
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickMore: function(ev) {
            ev.preventDefault();
            this.do_action({
                name: _t('Users'),
                type: 'ir.actions.act_window',
                view_mode: 'tree,form',
                res_model: 'res.users',
                domain: [['log_ids', '=', false]],
                context: {
                    search_default_no_share: true,
                },
                views: [[false, 'list'], [false, 'form']],
            });
        },
        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClickUser: function (ev) {
            ev.preventDefault();
            var user_id = $(e.currentTarget).data('user-id');
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'res.users',
                view_mode: 'form',
                views: [[false, 'form']],
                res_id: user_id,
            });
        },
        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onKeydownUserEmails: function (ev) {
            var $userEmails = this.$('.o_user_emails');
            var keyCodes = [$.ui.keyCode.TAB, $.ui.keyCode.COMMA, $.ui.keyCode.ENTER, $.ui.keyCode.SPACE];
            if (_.contains(keyCodes, ev.which)) {
                ev.preventDefault();
                this._createBadges();
            }
            // remove last badge on backspace
            if (ev.which === $.ui.keyCode.BACKSPACE && this.emails.length && !$userEmails.val()) {
                this._removeBadge(this.$('.o_web_settings_invitation_form .badge:last'));
            }
        },
    });

   widget_registry.add('res_config_invite_users', ResConfigInviteUsers);

});
