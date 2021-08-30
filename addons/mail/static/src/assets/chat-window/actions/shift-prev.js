/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Shift this chat window to previous visible position.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/shiftPrev
        [Action/params]
            chatWindow
        [Action/behavior]
            {ChatWindowManager/shiftPrev}
                [0]
                    @chatWindow
                    .{ChatWindow/manager}
                [1]
                    @chatWindow
`;
