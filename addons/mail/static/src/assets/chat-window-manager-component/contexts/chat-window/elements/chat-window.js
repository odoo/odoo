/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            chatWindow
        [Element/model]
            ChatWindowManagerComponent:chatWindow
        [Field/target]
            ChatWindowComponent
        [ChatWindowComponent/chatWindow]
            @record
            .{ChatWindowManagerComponent:chatWindow/chatWindow}
        [ChatWindowComponent/hasCloseAsBackButton]
            {Device/isMobile}
        [ChatWindowComponent/isExpandable]
            {Device/isMobile}
            .{isFalsy}
            .{&}
                @record
                .{ChatWindowManagerComponent:chatWindow/chatWindow}
                .{ChatWindow/thread}
        [ChatWindowComponent/isFullscreen]
            {Device/isMobile}
`;
