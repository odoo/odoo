/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/focusNextVisibleUnfoldedChatWindow
        [Action/params]
            chatWindow
        [Action/behavior]
            :nextVisibleUnfoldedChatWindow
                {ChatWindow/_getNextVisibleUnfoldedChatWindow}
                    @chatWindow
            {if}
                @nextVisibleUnfoldedChatWindow
            .{then}
                {ChatWindow/focus}
                    @nextVisibleUnfoldedChatWindow
`;
