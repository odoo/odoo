/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/focusPreviousVisibleUnfoldedChatWindow
        [Action/params]
            chatWindow
        [Action/behavior]
            :previousVisibleUnfoldedChatWindow
                {ChatWindow/_getNextVisibleUnfoldedChatWindow}
                    [0]
                        @chatWindow
                    [1]
                        [reverse]
                            true
            {if}
                @previousVisibleUnfoldedChatWindow
            .{then}
                {ChatWindow/focus}
                    @previousVisibleUnfoldedChatWindow
`;
