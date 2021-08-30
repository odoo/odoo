/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Notifies threadViews about the given message being just received.
        This can allow them adjust their scroll position if applicable.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_notifyThreadViewsMessageReceived
        [Action/params]
            messagingNotificationHandler
                [type]
                    MessagingNotificationHandler
            message
                [type]
                    Message
        [Action/behavior]
            {foreach}
                @message
                .{Message/threads}
            .{as}
                thread
            .{do}
                {foreach}
                    @thread
                    .{Thread/threadViews}
                .{as}
                    threadView
                .{do}
                    {ThreadView/addComponentHint}
                        [0]
                            @threadView
                        [1]
                            message-received
                        [2]
                            [message]
                                @message
`;
