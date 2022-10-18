/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Transition } from "@web/core/transition";

const { Component, onWillPatch } = owl;

export class MessageList extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'loadMoreRef', refName: 'loadMore' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
        /**
         * Snapshot computed during willPatch, which is used by patched.
         */
        this._willPatchSnapshot = undefined;
        this._onScrollThrottled = _.throttle(this._onScrollThrottled.bind(this), 100);
        onWillPatch(() => this._willPatch());
    }

    _willPatch() {
        if (!this.messageListView.exists()) {
            return;
        }
        this._willPatchSnapshot = {
            scrollHeight: this.messageListView.getScrollableElement().scrollHeight,
            scrollTop: this.messageListView.getScrollableElement().scrollTop,
        };
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {MessageListView}
     */
    get messageListView() {
        return this.props.record;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {boolean}
     */
    _isLoadMoreVisible() {
        const loadMore = this.messageListView.loadMoreRef.el;
        if (!loadMore) {
            return false;
        }
        const loadMoreRect = loadMore.getBoundingClientRect();
        const elRect = this.messageListView.getScrollableElement().getBoundingClientRect();
        const isInvisible = loadMoreRect.top > elRect.bottom || loadMoreRect.bottom < elRect.top;
        return !isInvisible;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {ScrollEvent} ev
     */
    onScroll(ev) {
        this._onScrollThrottled(ev);
    }

    /**
     * @private
     * @param {ScrollEvent} ev
     */
    _onScrollThrottled(ev) {
        if (!this.messageListView.exists()) {
            return;
        }
        if (!this.messageListView.getScrollableElement()) {
            // could be unmounted in the meantime (due to throttled behavior)
            return;
        }
        const scrollTop = this.messageListView.getScrollableElement().scrollTop;
        this.messaging.messagingBus.trigger('o-component-message-list-scrolled', {
            orderedMessages: this.messageListView.threadViewOwner.threadCache.orderedMessages,
            scrollTop,
            thread: this.messageListView.threadViewOwner.thread,
            threadViewer: this.messageListView.threadViewOwner.threadViewer,
        });
        this.messageListView.update({
            clientHeight: this.messageListView.getScrollableElement().clientHeight,
            scrollHeight: this.messageListView.getScrollableElement().scrollHeight,
            scrollTop: this.messageListView.getScrollableElement().scrollTop,
        });
        if (!this.messageListView.isLastScrollProgrammatic) {
            // Automatically scroll to new received messages only when the list is
            // currently fully scrolled.
            const hasAutoScrollOnMessageReceived = this.messageListView.isAtEnd;
            this.messageListView.threadViewOwner.update({ hasAutoScrollOnMessageReceived });
        }
        this.messageListView.threadViewOwner.threadViewer.saveThreadCacheScrollHeightAsInitial(this.messageListView.getScrollableElement().scrollHeight, this.messageListView.threadViewOwner.threadCache);
        this.messageListView.threadViewOwner.threadViewer.saveThreadCacheScrollPositionsAsInitial(scrollTop, this.messageListView.threadViewOwner.threadCache);
        if (
            !this.messageListView.isLastScrollProgrammatic &&
            this._isLoadMoreVisible() &&
            this.messageListView.threadViewOwner.threadCache
        ) {
            this.messageListView.threadViewOwner.threadCache.loadMoreMessages();
        }
        this.messageListView.checkMostRecentMessageIsVisible();
        this.messageListView.update({ isLastScrollProgrammatic: false });
    }

}

Object.assign(MessageList, {
    components: { Transition },
    props: { record: Object },
    template: 'mail.MessageList',
});

registerMessagingComponent(MessageList);
