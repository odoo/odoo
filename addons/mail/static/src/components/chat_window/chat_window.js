/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { isEventHandled } from '@mail/utils/utils';

const { Component } = owl;

export class ChatWindow extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'ChatWindow' });
        this._onClickedHeader = this._onClickedHeader.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ChatWindow}
     */
    get chatWindow() {
        return this.messaging && this.messaging.models['ChatWindow'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Save the scroll positions of the chat window in the store.
     * This is useful in order to remount chat windows and keep previous
     * scroll positions. This is necessary because when toggling on/off
     * home menu, the chat windows have to be remade from scratch.
     *
     * @private
     */
    _saveThreadScrollTop() {
        if (
            !this.chatWindow ||
            !this.chatWindow.threadView ||
            !this.chatWindow.threadView.messageListView ||
            !this.chatWindow.threadView.messageListView.component ||
            !this.chatWindow.threadViewer
        ) {
            return;
        }
        if (
            this.chatWindow.threadViewer.threadView &&
            this.chatWindow.threadViewer.threadView.componentHintList.length > 0
        ) {
            // the current scroll position is likely incorrect due to the
            // presence of hints to adjust it
            return;
        }
        this.chatWindow.threadViewer.saveThreadCacheScrollHeightAsInitial(
            this.chatWindow.threadView.messageListView.component.getScrollHeight()
        );
        this.chatWindow.threadViewer.saveThreadCacheScrollPositionsAsInitial(
            this.chatWindow.threadView.messageListView.component.getScrollTop()
        );
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on header of chat window. Usually folds the chat
     * window.
     *
     * @private
     */
    _onClickedHeader() {
        if (this.messaging.device.isMobile) {
            return;
        }
        if (this.chatWindow.isFolded) {
            this.chatWindow.unfold();
            this.chatWindow.focus();
        } else {
            this._saveThreadScrollTop();
            this.chatWindow.fold();
        }
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        if (!this.chatWindow) {
            // prevent crash during delete
            return;
        }
        switch (ev.key) {
            case 'Tab':
                ev.preventDefault();
                if (ev.shiftKey) {
                    this.chatWindow.focusPreviousVisibleUnfoldedChatWindow();
                } else {
                    this.chatWindow.focusNextVisibleUnfoldedChatWindow();
                }
                break;
            case 'Escape':
                if (isEventHandled(ev, 'ComposerTextInput.closeSuggestions')) {
                    break;
                }
                if (isEventHandled(ev, 'Composer.closeEmojisPopover')) {
                    break;
                }
                ev.preventDefault();
                this.chatWindow.focusNextVisibleUnfoldedChatWindow();
                this.chatWindow.close();
                break;
        }
    }

}

Object.assign(ChatWindow, {
    defaultProps: {
        hasCloseAsBackButton: false,
        isExpandable: false,
        isFullscreen: false,
    },
    props: {
        localId: String,
        hasCloseAsBackButton: { type: Boolean, optional: true },
        isExpandable: { type: Boolean, optional: true },
        isFullscreen: { type: Boolean, optional: true },
    },
    template: 'mail.ChatWindow',
});

registerMessagingComponent(ChatWindow);
