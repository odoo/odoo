/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Shift this chat window to next visible position.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/shiftNext
        [Action/params]
            chatWindow
        [Action/behavior]
            {ChatWindowManager/shiftNext}
                [0]
                    @chatWindow
                    .{ChatWindow/manager}
                [1]
                    @chatWindow
`;
