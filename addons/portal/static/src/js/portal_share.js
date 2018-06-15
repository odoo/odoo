odoo.define('portal.share', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var SystrayMenu = require('web.SystrayMenu');
var WebClient = require('web.WebClient');
var web_settings_dashboard = require('web_settings_dashboard');
var Widget = require('web.Widget');

var _t = core._t;

var PortalInvitation = web_settings_dashboard.DashboardInvitations.extend({
    template: 'PortalUserInvitations',

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickInvite: function (ev) {
        this._createBadges();
        if (!this.emails.length) {
            return $.when();
        }
        return this._rpc({
            model: 'res.users',
            method: 'web_dashboard_create_users',
            args: [this.emails],
        });
    },
});

var PortalShareDoc = Widget.extend({
    template: 'PortalSharingIcon',
    events: {
        "click": "_onClick",
    },

    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var def = this.getSession().user_has_group('base.group_erp_manager').then(function (has_group){
            self.use_invite = has_group;
        });
        return $.when(def, this._super(this, arguments)).then(function () {
            core.bus.on('share_action', self, self._toggleShareAction);
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * open user invitation dialog
     * @private
     */
    _openInvitationDialog: function () {
        this.$content = $("<div>");
        var invitation = new PortalInvitation(this, {});
        invitation.appendTo(this.$content);
        return new Dialog(this, {
            title: _t('Invite New Users'),
            size: 'medium',
            $content: this.$content,
            buttons: [{
                text: 'Invite',
                classes: 'btn-primary',
                click: function (ev) {
                    var self = this;
                    invitation._onClickInvite(ev).then(function (data) {
                        self.close(true);
                    });
                },
            }, {
                text: 'Cancel',
                close: true
            }]
        }).open();
    },

    /**
     * Update the system tray icon for share document, based on view type
     * Show Share Icon only if 1) action context has share_icon True 2) form view of portal.mixin inherited object
     * @private
     */
    _toggleShareAction: function (widget) {
        this._controller = widget;
        if (widget && widget.viewType === 'form') {
            if (widget.activeActions && widget.activeActions.share) {
                this.$el.removeClass('o_hidden');
            } else {
                this.$el.addClass('o_hidden');
            }
        } else {
            this._controller = null;
            if (this.use_invite && widget && widget.action && widget.action.context.share_icon) {
                this.$el.removeClass('o_hidden');
            } else {
                this.$el.addClass('o_hidden');
            }
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /*
     * Opens Share document wizard, loads action and call that action with additional context(active_id and active_model)
     *@private
     */
    _onClick: function (ev) {
        ev.preventDefault();
        var self = this;
        var additional_context = {};
        if (!this._controller) {
            return this._openInvitationDialog();
        }
        if (this._controller) {
            var renderer = this._controller.renderer;
            var state = renderer.state;
            var resID = state.data.id;
            if (!resID) {
                this.do_warn(_t("Record does not exist!"), _t("Please, Save this record before sharing."));
                return $.Deferred().reject();
            }
            additional_context = {
                'active_id': resID,
                'active_model': state.model,
            };
        }
        return self.do_action('portal.mail_invite_share_action', {
            additional_context: additional_context,
            on_close: function () {
                self._controller.reload();
            },
        });
    },
});

WebClient.include({

    /**
     * @override
     */
    current_action_updated: function (action, controller) {
        this._super.apply(this, arguments);
        core.bus.trigger('share_action', controller && controller.widget);
    },
});

SystrayMenu.Items.push(PortalShareDoc);

});
