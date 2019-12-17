odoo.define('mail.widget.Discuss', function (require) {
'use strict';

const DiscussComponent = require('mail.component.Discuss');
const InvitePartnerDialog = require('mail.widget.DiscussInvitePartnerDialog');

const AbstractAction = require('web.AbstractAction');
const { _t, action_registry, qweb } = require('web.core');

const DiscussWidget = AbstractAction.extend({
    template: 'mail.widget.Discuss',
    hasControlPanel: true,
    loadControlPanel: true,
    withSearchBar: true,
    searchMenuTypes: ['filter', 'favorite'],
    custom_events: {
        search: '_onSearch',
    },
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

        // render buttons in control panel
        this.$buttons = $(qweb.render('mail.widget.DiscussControlButtons'));
        this.$buttons.find('button').css({ display:'inline-block' });
        this.$buttons.on('click', '.o_invite', ev => this._onClickInvite(ev));
        this.$buttons.on('click', '.o_mark_all_read', ev => this._onClickMarkAllAsRead(ev));
        this.$buttons.on('click', '.o_mobile_new_channel', ev => this._onClickMobileNewChannel(ev));
        this.$buttons.on('click', '.o_mobile_new_message', ev => this._onClickMobileNewMessage(ev));
        this.$buttons.on('click', '.o_unstar_all', ev => this._onClickUnstarAll(ev));

        // control panel attributes
        this.action = action;
        this.actionManager = parent;
        this.controlPanelParams.modelName = 'mail.message';
        this.options = options;

        this.component = undefined;

        this._initActiveThreadLocalId = this.options.active_id ||
            (this.action.context && this.action.context.active_id) ||
            (this.action.params && this.action.params.default_active_id) ||
            'mail.box_inbox';
        this._lastPushStateActiveThreadLocalId = null;
    },
    /**
     * @override
     */
    async willStart() {
        await this._super(...arguments);
        this.env = this.call('messaging', 'getMessagingEnv');
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
        DiscussComponent.env = this.env;
        this.component = new DiscussComponent(null, {
            initActiveThreadLocalId: this._initActiveThreadLocalId,
        });
        this._pushStateActionManagerEventListener = ev => {
            ev.stopPropagation();
            if (this._lastPushStateActiveThreadLocalId === ev.detail.activeThreadLocalId) {
                return;
            }
            this._pushStateActionManager(ev.detail.activeThreadLocalId);
            this._lastPushStateActiveThreadLocalId = ev.detail.activeThreadLocalId;
        };
        this._showRainbowManEventListener = ev => {
            ev.stopPropagation();
            this._showRainbowMan();
        };
        this._updateControlPanelEventListener = ev => {
            ev.stopPropagation();
            this._updateControlPanel();
        };

        this.el.addEventListener(
            'o-push-state-action-manager',
            this._pushStateActionManagerEventListener
        );
        this.el.addEventListener(
            'o-show-rainbow-man',
            this._showRainbowManEventListener
        );
        this.el.addEventListener(
            'o-update-control-panel',
            this._updateControlPanelEventListener
        );
        return this.component.mount(this.$el[0]);
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
        this.el.removeEventListener(
            'o-update-control-panel',
            this._updateControlPanelEventListener
        );
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} activeThreadLocalId
     */
    _pushStateActionManager(activeThreadLocalId) {
        this.actionManager.do_push_state({
            action: this.action.id,
            active_id: activeThreadLocalId,
        });
    },
    /**
     * @private
     */
    _showRainbowMan() {
        this.trigger_up('show_effect', {
            message: _t("Congratulations, your inbox is empty!"),
            type: 'rainbow_man',
        });
    },
    /**
     * @private
     */
    _updateControlPanel() {
        const activeThreadLocalId = this.component.storeProps.activeThreadLocalId;
        const hasMessages = this.component.hasActiveThreadMessages();
        const isMobile = this.component.storeProps.isMobile;
        const activeThread = this.component.storeProps.activeThread;
        const activeMobileNavbarTabId = this.component.storeProps.activeMobileNavbarTabId;
        // Invite
        if (activeThread && activeThread.channel_type === 'channel') {
            this.$buttons.find('.o_invite').removeClass('o_hidden');
        } else {
            this.$buttons.find('.o_invite').addClass('o_hidden');
        }
        // Mark All Read
        if (activeThreadLocalId === 'mail.box_inbox') {
            this.$buttons.find('.o_mark_all_read').removeClass('o_hidden')
                .prop('disabled', !hasMessages);
        }
        if (
            activeThreadLocalId !== 'mail.box_inbox' ||
            activeMobileNavbarTabId !== 'mailbox'
        ) {
            this.$buttons.find('.o_mark_all_read').addClass('o_hidden');
        }
        // Unstar All
        if (activeThreadLocalId === 'mail.box_starred') {
            this.$buttons.find('.o_unstar_all').removeClass('o_hidden')
                .prop('disabled', !hasMessages);
        }
        if (
            activeThreadLocalId !== 'mail.box_starred' ||
            activeMobileNavbarTabId !== 'mailbox'
        ) {
            this.$buttons.find('.o_unstar_all').addClass('o_hidden');
        }
        // Mobile: Add channel
        if (isMobile && activeMobileNavbarTabId === 'channel') {
            this.$buttons.find('.o_mobile_new_channel').removeClass('o_hidden');
        } else {
            this.$buttons.find('.o_mobile_new_channel').addClass('o_hidden');
        }
        // Mobile: Add message
        if (isMobile && activeMobileNavbarTabId === 'chat') {
            this.$buttons.find('.o_mobile_new_message').removeClass('o_hidden');
        } else {
            this.$buttons.find('.o_mobile_new_message').addClass('o_hidden');
        }
        if (isMobile) {
            this._setTitle(_t("Discuss"));
        } else {
            let title;
            if (activeThread) {
                const activeThreadName = this.env.store.getters.threadName(activeThreadLocalId);
                const prefix =
                    activeThread.channel_type === 'channel' &&
                    activeThread.public !== 'private'
                    ? '#'
                    : '';
                title = `${prefix}${activeThreadName}`;
            } else {
                title = _t("Discuss");
            }
            this._setTitle(title);
        }
        this.updateControlPanel({
            cp_content: {
                $buttons: this.$buttons,
            },
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
            activeThreadLocalId: this.component.storeProps.activeThreadLocalId,
            messagingEnv: this.env,
        }).open();
    },
    /**
     * @private
     */
    _onClickMarkAllAsRead() {
        this.env.store.dispatch('markAllMessagesAsRead', { domain: this.domain });
    },
    /**
     * @private
     */
    _onClickMobileNewChannel() {
        this.component.doMobileNewChannel();
    },
    /**
     * @private
     */
    _onClickMobileNewMessage() {
        this.component.doMobileNewMessage();
    },
    /**
     * @private
     */
    _onClickUnstarAll() {
        this.env.store.dispatch('unstarAllMessages');
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Array} ev.data.domain
     */
    _onSearch(ev) {
        ev.stopPropagation();
        this.component.updateDomain(ev.data.domain);
    },
});

action_registry.add('mail.widget.discuss', DiscussWidget);

return DiscussWidget;

});
