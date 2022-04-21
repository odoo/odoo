/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import {
    isEventHandled,
    markEventHandled,
} from '@mail/utils/utils';

const { Component } = owl;

export class ChatWindowHeader extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.chat_window}
     */
    get chatWindow() {
        return this.messaging && this.messaging.models['mail.chat_window'].get(this.props.chatWindowLocalId);
    }

    /**
     * @returns {string}
     */
    get shiftNextText() {
        if (this.messaging.locale.textDirection === 'rtl') {
            return this.env._t("Shift left");
        }
        return this.env._t("Shift right");
    }

    /**
     * @returns {string}
     */
    get shiftPrevText() {
        if (this.messaging.locale.textDirection === 'rtl') {
            return this.env._t("Shift right");
        }
        return this.env._t("Shift left");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        if (
            isEventHandled(ev, 'ChatWindow.onClickCommand') ||
            isEventHandled(ev, 'ChatWindowHeader.ClickShiftNext') ||
            isEventHandled(ev, 'ChatWindowHeader.ClickShiftPrev') ||
            isEventHandled(ev, 'ChatWindow.onClickHideMemberList') ||
            isEventHandled(ev, 'ChatWindow.onClickShowMemberList')
        ) {
            return;
        }
        const chatWindow = this.chatWindow;
        this.trigger('o-clicked', { chatWindow });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickClose(ev) {
        ev.stopPropagation();
        if (!this.chatWindow) {
            return;
        }
        this.chatWindow.close();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickCamera(ev) {
        ev.stopPropagation();
        if (this.chatWindow.thread.hasPendingRtcRequest) {
            return;
        }
        await this.chatWindow.thread.toggleCall({ startWithVideo: true });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickPhone(ev) {
        ev.stopPropagation();
        if (this.chatWindow.thread.hasPendingRtcRequest) {
            return;
        }
        await this.chatWindow.thread.toggleCall();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickExpand(ev) {
        ev.stopPropagation();
        this.chatWindow.expand();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickShiftPrev(ev) {
        markEventHandled(ev, 'ChatWindowHeader.ClickShiftPrev');
        if (this.props.saveThreadScrollTop) {
            this.props.saveThreadScrollTop();
        }
        this.chatWindow.shiftPrev();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickShiftNext(ev) {
        markEventHandled(ev, 'ChatWindowHeader.ClickShiftNext');
        if (this.props.saveThreadScrollTop) {
            this.props.saveThreadScrollTop();
        }
        this.chatWindow.shiftNext();
    }

}

Object.assign(ChatWindowHeader, {
    defaultProps: {
        hasCloseAsBackButton: false,
        isExpandable: false,
    },
    props: {
        chatWindowLocalId: String,
        hasCloseAsBackButton: Boolean,
        isExpandable: Boolean,
        saveThreadScrollTop: {
            type: Function,
            optional: true,
        },
    },
    template: 'mail.ChatWindowHeader',
});

registerMessagingComponent(ChatWindowHeader);
