/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { isEventHandled } from '@mail/utils/utils';

const { Component } = owl;

export class ChatWindowHeader extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ChatWindow}
     */
    get chatWindow() {
        return this.props.chatWindow;
    }

    /**
     * @returns {ChatWindowHeaderView}
     */
     get chatWindowHeaderView() {
        return this.props.record;
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
        if (this.props.onClicked) {
            this.props.onClicked({ chatWindow });
        }
    }

}

Object.assign(ChatWindowHeader, {
    props: {
        chatWindow: Object,
        record: Object,
        onClicked: {
            type: Function,
            optional: true,
        },
    },
    template: 'mail.ChatWindowHeader',
});

registerMessagingComponent(ChatWindowHeader);
