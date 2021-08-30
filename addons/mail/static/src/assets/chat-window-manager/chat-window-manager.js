/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ChatWindowManager
        [Model/fields]
            allOrdered
            allOrderedHidden
            allOrderedVisible
            chatWindows
            hasHiddenChatWindows
            hasVisibleChatWindows
            isHiddenMenuOpen
            lastVisible
            newMessageChatWindow
            unreadHiddenConversationAmount
            visual
        [Model/id]
            ChatWindowManager/messaging
        [Model/actions]
            ChatWindowManager/closeAll
            ChatWindowManager/closeHiddenMenu
            ChatWindowManager/closeThread
            ChatWindowManager/openHiddenMenu
            ChatWindowManager/openNewMessage
            ChatWindowManager/openThread
            ChatWindowManager/shiftNext
            ChatWindowManager/shiftPrev
            ChatWindowManager/start
            ChatWindowManager/stop
            ChatWindowManager/swap
`;
