/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Makes this chat window visible by swapping it with the last visible
        chat window, or do nothing if it is already visible.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/makeVisible
        [Action/params]
            chatWindow
        [Action/behavior]
            {if}
                @chatWindow
                .{ChatWindow/isVisible}
            .{then}
                {break}
            {ChatWindowManager/swap}
                [0]
                    @chatWindow
                    .{ChatWindow/manager}
                [1]
                    @chatWindow
                [2]
                    @chatWindow
                    .{ChatWindow/manager}
                    .{ChatWindowManager/lastVisible}
`;
