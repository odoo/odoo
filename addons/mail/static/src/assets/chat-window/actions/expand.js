/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatWindow/expand
        [Action/params]
            chatWindow
        [Action/behavior]
            {if}
                @chatWindow
                .{ChatWindow/thread}
            .{then}
                {Thread/open}
                    [0]
                        @chatWindow
                        .{ChatWindow/thread}
                    [1]
                        [expanded]
                            true
`;
