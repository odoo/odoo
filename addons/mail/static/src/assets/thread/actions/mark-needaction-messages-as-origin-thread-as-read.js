/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Mark as read all needaction messages with this thread as origin.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/markNeedactionMessagesAsOriginThreadAsRead
        [Action/params]
            thread
                [type]
                    Thread
        [Action/behavior]
            {Record/doAsync}
                [0]
                    @thread
                [1]
                    {Message/markMessagesAsRead}
                        @thread
                        .{Thread/needactionMessagesAsOriginThread}
`;
