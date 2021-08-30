/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Close all chat windows.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindowManager/closeAll
        [Action/params]
            chatWindowManager
                [type]
                    ChatWindowManager
        [Action/behavior]
            {foreach}
                @chatWindowManager
                .{ChatWindowManager/allOrdered}
            .{as}
                chatWindow
            .{do}
                {ChatWindow/close}
                    @chatWindow
`;
