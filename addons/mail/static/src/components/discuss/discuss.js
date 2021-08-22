/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { link, unlink } from '@mail/model/model_field_command';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { useService } from "@web/core/utils/hooks";

const { Component } = owl;
const { useRef } = owl.hooks;

export class Discuss extends Component {
    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.effect = useService('effect');
        this._updateLocalStoreProps();
        /**
         * Reference of the composer. Useful to focus it.
         */
        this._composerRef = useRef('composer');
        /**
         * Reference of the ThreadView. Useful to focus it.
         */
        this._threadViewRef = useRef('threadView');
        // bind since passed as props
        this._onMobileAddItemHeaderInputSelect = this._onMobileAddItemHeaderInputSelect.bind(this);
        this._onMobileAddItemHeaderInputSource = this._onMobileAddItemHeaderInputSource.bind(this);
        this._lastPushStateActiveThread = null;

        useUpdate({ func: () => {
            if (!this.discuss) {
                return;
            }
            this.discuss.update({ isOpen: true });
            if (!this.discuss.thread && this.messaging.isInitialized) {
                this.discuss.openInitThread();
            }
            if (this.discuss.thread && this._lastPushStateActiveThread !== this.discuss.thread) {
                this.env.services.router.pushState({
                    action: this.props.action.id,
                    active_id: this.discuss.activeId,
                });
                this._lastPushStateActiveThread = this.discuss.thread;
            }
            if (
                this.discuss.thread &&
                this.discuss.thread === this.messaging.inbox &&
                this.discuss.threadView &&
                this._lastThreadCache === this.discuss.threadView.threadCache.localId &&
                this._lastThreadCounter > 0 && this.discuss.thread.counter === 0
            ) {
                this.effect.add('rainbowman', { message: this.env._t("Congratulations, your inbox is empty!") });
            }
            this._updateLocalStoreProps();
        } });
        this.env.services.messaging.modelManager.messagingCreatedPromise.then(() => {
            const initActiveId = (
                (this.props.action.context && this.props.action.context.active_id) ||
                (this.props.action.params && this.props.action.params.default_active_id) ||
                'mail.box_inbox'
            );
            this.messaging.discuss.update({ initActiveId });
        });
    }

    willUnmount() {
        if (this.discuss) {
            this.discuss.close();
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {string}
     */
    get addChannelInputPlaceholder() {
        return this.env._t("Create or search channel...");
    }

    /**
     * @returns {string}
     */
    get addChatInputPlaceholder() {
        return this.env._t("Search user...");
    }

    /**
     * @returns {mail.discuss}
     */
    get discuss() {
        return this.messaging && this.messaging.discuss;
    }

    /**
     * @returns {Object[]}
     */
    mobileNavbarTabs() {
        return [{
            icon: 'fa fa-inbox',
            id: 'mailbox',
            label: this.env._t("Mailboxes"),
        }, {
            icon: 'fa fa-user',
            id: 'chat',
            label: this.env._t("Chat"),
        }, {
            icon: 'fa fa-users',
            id: 'channel',
            label: this.env._t("Channel"),
        }];
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateLocalStoreProps() {
        if (!this.discuss) {
            return;
        }
        /**
         * Locally tracked store props `activeThreadCache`.
         * Useful to set scroll position from last stored one and to display
         * rainbox man on inbox.
         */
        this._lastThreadCache = (
            this.discuss.threadView &&
            this.discuss.threadView.threadCache &&
            this.discuss.threadView.threadCache.localId
        );
        /**
         * Locally tracked store props `threadCounter`.
         * Useful to display the rainbow man on inbox.
         */
        this._lastThreadCounter = (
            this.discuss.thread &&
            this.discuss.thread.counter
        );
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onFocusinComposer(ev) {
        this.discuss.update({ isDoFocus: false });
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onHideMobileAddItemHeader(ev) {
        ev.stopPropagation();
        this.discuss.clearIsAddingItem();
    }

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onMobileAddItemHeaderInputSelect(ev, ui) {
        const discuss = this.discuss;
        if (discuss.isAddingChannel) {
            discuss.handleAddChannelAutocompleteSelect(ev, ui);
        } else {
            discuss.handleAddChatAutocompleteSelect(ev, ui);
        }
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onMobileAddItemHeaderInputSource(req, res) {
        if (this.discuss.isAddingChannel) {
            this.discuss.handleAddChannelAutocompleteSource(req, res);
        } else {
            this.discuss.handleAddChatAutocompleteSource(req, res);
        }
    }

    /**
     * @private
     */
    _onReplyingToMessageMessagePosted() {
        this.env.services.notification.add(
            _.str.sprintf(
                this.env._t(`Message posted on "%s"`),
                this.discuss.replyingToMessage.originThread.displayName
            ),
            { type: 'info' },
        );
        this.discuss.clearReplyingToMessage();
    }

    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {string} ev.detail.tabId
     */
    _onSelectMobileNavbarTab(ev) {
        ev.stopPropagation();
        if (this.discuss.activeMobileNavbarTabId === ev.detail.tabId) {
            return;
        }
        this.discuss.clearReplyingToMessage();
        this.discuss.update({ activeMobileNavbarTabId: ev.detail.tabId });
        if (
            this.discuss.activeMobileNavbarTabId === 'mailbox' &&
            (!this.discuss.thread || this.discuss.thread.model !== 'mailbox')
        ) {
            this.discuss.update({ thread: link(this.messaging.inbox) });
        }
        if (this.discuss.activeMobileNavbarTabId !== 'mailbox') {
            this.discuss.update({ thread: unlink() });
        }
        if (this.discuss.activeMobileNavbarTabId !== 'chat') {
            this.discuss.update({ isAddingChat: false });
        }
        if (this.discuss.activeMobileNavbarTabId !== 'channel') {
            this.discuss.update({ isAddingChannel: false });
        }
    }

}

Object.assign(Discuss, {
    props: {
        action: Object,
        actionId: Number,
        breadcrumbs: Object,
        registerCallback: Function,
        resId: {
            Number,
            optional: true,
        },
    },
    template: 'mail.Discuss',
});

registerMessagingComponent(Discuss);
