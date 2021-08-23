/** @odoo-module **/

import { getMessagingComponent } from "@mail/utils/messaging_component";

import AbstractAction from 'web.AbstractAction';

const { Component } = owl;

export const DiscussWidget = AbstractAction.extend({
    template: 'mail.widgets.Discuss',
    /**
     * @override {web.AbstractAction}
     * @param {web.ActionManager} parent
     * @param {Object} action
     * @param {Object} [action.context]
     * @param {string} [action.context.active_id]
     * @param {Object} [action.params]
     * @param {string} [action.params.default_active_id]
     * @param {Object} [options={}]
     */
    init(parent, action, options={}) {
        this._super(...arguments);

        // control panel attributes
        this.action = action;
        this.actionManager = parent;
        this.discuss = undefined;
        this.options = options;

        this.component = undefined;

        this._lastPushStateActiveThread = null;
        this.env = Component.env;
        Component.env.services.messaging.modelManager.messagingCreatedPromise.then(() => {
            const messaging = Component.env.services.messaging.modelManager.messaging;
            const initActiveId = this.options.active_id ||
                (this.action.context && this.action.context.active_id) ||
                (this.action.params && this.action.params.default_active_id) ||
                'mail.box_inbox';
            this.discuss = messaging.discuss;
            this.discuss.update({ initActiveId });
        });
    },
    /**
     * @override {web.AbstractAction}
     */
    destroy() {
        if (this.component) {
            this.component.destroy();
            this.component = undefined;
        }
        if (this.$buttons) {
            this.$buttons.off().remove();
        }
        this._super(...arguments);
    },
    /**
     * @override {web.AbstractAction}
     */
    on_attach_callback() {
        this._super(...arguments);
        if (this.component) {
            // prevent twice call to on_attach_callback (FIXME)
            return;
        }
        const DiscussComponent = getMessagingComponent("Discuss");
        this.component = new DiscussComponent();
        this._pushStateActionManagerEventListener = ev => {
            ev.stopPropagation();
            if (this._lastPushStateActiveThread === this.discuss.thread) {
                return;
            }
            this._pushStateActionManager();
            this._lastPushStateActiveThread = this.discuss.thread;
        };
        this._showRainbowManEventListener = ev => {
            ev.stopPropagation();
            this._showRainbowMan();
        };
        this.el.addEventListener(
            'o-push-state-action-manager',
            this._pushStateActionManagerEventListener
        );
        this.el.addEventListener(
            'o-show-rainbow-man',
            this._showRainbowManEventListener
        );
        return this.component.mount(this.el);
    },
    /**
     * @override {web.AbstractAction}
     */
    on_detach_callback() {
        this._super(...arguments);
        if (this.component) {
            this.component.destroy();
        }
        this.component = undefined;
        this.el.removeEventListener(
            'o-push-state-action-manager',
            this._pushStateActionManagerEventListener
        );
        this.el.removeEventListener(
            'o-show-rainbow-man',
            this._showRainbowManEventListener
        );
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _pushStateActionManager() {
        this.actionManager.do_push_state({
            action: this.action.id,
            active_id: this.discuss.activeId,
        });
    },
    /**
     * @private
     */
    _showRainbowMan() {
        this.trigger_up('show_effect', {
            message: this.env._t("Congratulations, your inbox is empty!"),
            type: 'rainbow_man',
        });
    },
<<<<<<< HEAD
=======
    /**
     * @private
     */
    _updateControlPanel() {
        // Invite
        if (this._shouldHaveInviteButton()) {
            this.$buttons.find('.o_invite').removeClass('o_hidden');
        } else {
            this.$buttons.find('.o_invite').addClass('o_hidden');
        }
        // Mark All Read
        if (
            this.discuss.threadView &&
            this.discuss.thread &&
            this.discuss.thread === this.env.messaging.inbox
        ) {
            this.$buttons
                .find('.o_widget_Discuss_controlPanelButtonMarkAllRead')
                .removeClass('o_hidden')
                .prop('disabled', this.discuss.threadView.messages.length === 0);
        } else {
            this.$buttons
                .find('.o_widget_Discuss_controlPanelButtonMarkAllRead')
                .addClass('o_hidden');
        }
        // Unstar All
        if (
            this.discuss.threadView &&
            this.discuss.thread &&
            this.discuss.thread === this.env.messaging.starred
        ) {
            this.$buttons
                .find('.o_unstar_all')
                .removeClass('o_hidden')
                .prop('disabled', this.discuss.threadView.messages.length === 0);
        } else {
            this.$buttons
                .find('.o_unstar_all')
                .addClass('o_hidden');
        }
        // Mobile: Add channel
        if (
            this.env.messaging.device.isMobile &&
            this.discuss.activeMobileNavbarTabId === 'channel'
        ) {
            this.$buttons
                .find('.o_mobile_new_channel')
                .removeClass('o_hidden');
        } else {
            this.$buttons
                .find('.o_mobile_new_channel')
                .addClass('o_hidden');
        }
        // Mobile: Add message
        if (
            this.env.messaging.device.isMobile &&
            this.discuss.activeMobileNavbarTabId === 'chat'
        ) {
            this.$buttons
                .find('.o_mobile_new_message')
                .removeClass('o_hidden');
        } else {
            this.$buttons
                .find('.o_mobile_new_message')
                .addClass('o_hidden');
        }
        // Select All & Unselect All
        const $selectAll = this.$buttons.find('.o_widget_Discuss_controlPanelButtonSelectAll');
        const $unselectAll = this.$buttons.find('.o_widget_Discuss_controlPanelButtonUnselectAll');

        if (
            this.discuss.threadView &&
            (
                this.discuss.threadView.checkedMessages.length > 0 ||
                this.discuss.threadView.uncheckedMessages.length > 0
            )
        ) {
            $selectAll.removeClass('o_hidden');
            $selectAll.toggleClass('disabled', this.discuss.threadView.uncheckedMessages.length === 0);
            $unselectAll.removeClass('o_hidden');
            $unselectAll.toggleClass('disabled', this.discuss.threadView.checkedMessages.length === 0);
        } else {
            $selectAll.addClass('o_hidden');
            $selectAll.addClass('disabled');
            $unselectAll.addClass('o_hidden');
            $unselectAll.addClass('disabled');
        }

        // Moderation Actions
        const $moderationButtons = this.$buttons.find('.o_widget_Discuss_controlPanelButtonModeration');
        if (
            this.discuss.threadView &&
            this.discuss.threadView.checkedMessages.length > 0 &&
            this.discuss.threadView.checkedMessages.filter(
                message => !message.isModeratedByCurrentPartner
            ).length === 0
        ) {
            $moderationButtons.removeClass('o_hidden');
        } else {
            $moderationButtons.addClass('o_hidden');
        }

        let title;
        if (this.env.messaging.device.isMobile || !this.discuss.thread) {
            title = this.env._t("Discuss");
        } else {
            const prefix =
                this.discuss.thread.channel_type === 'channel' &&
                this.discuss.thread.public !== 'private'
                ? '#'
                : '';
            title = `${prefix}${this.discuss.thread.displayName}`;
        }

        this.updateControlPanel({
            cp_content: {
                $buttons: this.$buttons,
            },
            title,
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickInvite() {
        new InvitePartnerDialog(this, {
            activeThreadLocalId: this.discuss.thread.localId,
            messagingEnv: this.env,
        }).open();
    },
    /**
     * @private
     */
    _onClickMarkAllAsRead() {
        const domain = this.discuss.stringifiedDomain ? JSON.parse(this.discuss.stringifiedDomain) : undefined;
        this.env.models['mail.message'].markAllAsRead(domain);
    },
    /**
     * @private
     */
    _onClickMobileNewChannel() {
        this.discuss.update({ isAddingChannel: true });
    },
    /**
     * @private
     */
    _onClickMobileNewMessage() {
        this.discuss.update({ isAddingChat: true });
    },
    /**
     * @private
     */
    _onClickModerationAccept() {
        this.env.models['mail.message'].moderate(
            this.discuss.threadView.checkedMessages,
            'accept'
        );
    },
    /**
     * @private
     */
    _onClickModerationDiscard() {
        this.discuss.update({ hasModerationDiscardDialog: true });
    },
    /**
     * @private
     */
    _onClickModerationReject() {
        this.discuss.update({ hasModerationRejectDialog: true });
    },
    /**
     * @private
     */
    _onClickSelectAll() {
        this.env.models['mail.message'].checkAll(
            this.discuss.thread,
            this.discuss.stringifiedDomain
        );
    },
    /**
     * @private
     */
    _onClickUnselectAll() {
        this.env.models['mail.message'].uncheckAll(
            this.discuss.thread,
            this.discuss.stringifiedDomain
        );
    },
    /**
     * @private
     */
    _onClickUnstarAll() {
        this.env.models['mail.message'].unstarAll();
    },
    /**
     * @private
     * @param {Object} searchQuery
     */
    _onSearch: function (searchQuery) {
        this.discuss.update({
            stringifiedDomain: JSON.stringify(searchQuery.domain),
        });
    },
});

action_registry.add('mail.widgets.discuss', DiscussWidget);

return DiscussWidget;

>>>>>>> d27b99f0000... temp
});
