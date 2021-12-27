/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';

const { Component } = owl;
const { onWillUnmount } = owl.hooks;

export class Discuss extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this._updateLocalStoreProps();
        useUpdate({ func: () => this._update() });
        onWillUnmount(() => this._willUnmount());
    }

    _update() {
        if (!this.discuss) {
            return;
        }
        this.discuss.update({ isOpen: true });
        if (this.discuss.thread) {
            this.trigger('o-push-state-action-manager');
        } else if (!this._activeThreadCache && this.discuss.messaging.isInitialized) {
            this.discuss.openInitThread();
        }
        if (
            this.discuss.thread &&
            this.discuss.thread === this.messaging.inbox &&
            this.discuss.threadView &&
            this._lastThreadCache === this.discuss.threadView.threadCache.localId &&
            this._lastThreadCounter > 0 && this.discuss.thread.counter === 0
        ) {
            this.trigger('o-show-rainbow-man');
        }
        this._activeThreadCache = this.discuss.threadView && this.discuss.threadView.threadCache;
        this._updateLocalStoreProps();
    }

    _willUnmount() {
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
     * @returns {Discuss}
     */
    get discuss() {
        return this.messaging && this.messaging.discuss;
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

}

Object.assign(Discuss, {
    props: {},
    template: 'mail.Discuss',
});

registerMessagingComponent(Discuss);
