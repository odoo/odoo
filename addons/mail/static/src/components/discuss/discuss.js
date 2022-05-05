/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { LegacyComponent } from '@web/legacy/legacy_component';
import { useWowlService } from '@web/legacy/utils';

export class Discuss extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        this.routerService = useWowlService('router');
        this.effectService = useWowlService('effect');
        this._lastPushStateActiveThread = null;
        this._updateLocalStoreProps();
        // bind since passed as props
        this._onMobileAddItemHeaderInputSource = this._onMobileAddItemHeaderInputSource.bind(this);
        useUpdate({ func: () => this._update() });
        this._onHideMobileAddItemHeader = this._onHideMobileAddItemHeader.bind(this);
    }

    _update() {
        if (!this.discussView) {
            return;
        }
        if (this.discussView.discuss.thread) {
            if (this._lastPushStateActiveThread === this.discussView.discuss.thread) {
                return;
            }
            this.routerService.pushState({
                action: this.discussView.actionId,
                active_id: this.discussView.discuss.activeId,
            });
            this._lastPushStateActiveThread = this.discussView.discuss.thread;
        }
        if (
            this.discussView.discuss.thread &&
            this.discussView.discuss.thread === this.messaging.inbox &&
            this.discussView.discuss.threadView &&
            this._lastThreadCache === this.discussView.discuss.threadView.threadCache.localId &&
            this._lastThreadCounter > 0 && this.discussView.discuss.thread.counter === 0
        ) {
            this.effectService.add({
                message: this.env._t("Congratulations, your inbox is empty!"),
            });
        }
        this._updateLocalStoreProps();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {DiscussView}
     */
    get discussView() {
        return this.messaging && this.messaging.models['DiscussView'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateLocalStoreProps() {
        if (!this.discussView) {
            return;
        }
        /**
         * Locally tracked store props `activeThreadCache`.
         * Useful to set scroll position from last stored one and to display
         * rainbox man on inbox.
         */
        this._lastThreadCache = (
            this.discussView.discuss.threadView &&
            this.discussView.discuss.threadView.threadCache &&
            this.discussView.discuss.threadView.threadCache.localId
        );
        /**
         * Locally tracked store props `threadCounter`.
         * Useful to display the rainbow man on inbox.
         */
        this._lastThreadCounter = (
            this.discussView.discuss.thread &&
            this.discussView.discuss.thread.counter
        );
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onHideMobileAddItemHeader() {
        if (!this.discussView) {
            return;
        }
        this.discussView.discuss.clearIsAddingItem();
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onMobileAddItemHeaderInputSource(req, res) {
        if (!this.discussView) {
            return;
        }
        if (this.discussView.discuss.isAddingChannel) {
            this.discussView.discuss.handleAddChannelAutocompleteSource(req, res);
        } else {
            this.discussView.discuss.handleAddChatAutocompleteSource(req, res);
        }
    }

}

Object.assign(Discuss, {
    props: { localId: String },
    template: 'mail.Discuss',
});

registerMessagingComponent(Discuss);
