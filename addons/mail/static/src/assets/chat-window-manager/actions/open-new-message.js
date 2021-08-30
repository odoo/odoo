/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindowManager/openNewMessage
        [Action/params]
            record
                [type]
                    ChatWindowManager
        [Action/behavior]
            {if}
                @record
                .{ChatWindowManager/newMessageChatWindow}
                .{isFalsy}
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [ChatWindowManager/newMessageChatWindow]
                            {Record/insert}
                                [Record/models]
                                    ChatWindow
                                [ChatWindow/manager]
                                    @record
            {ChatWindow/makeActive}
                @record
                .{ChatWindowManager/newMessageChatWindow}
`;
