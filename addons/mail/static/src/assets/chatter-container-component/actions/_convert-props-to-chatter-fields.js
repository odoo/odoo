/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ChatterContainerComponent/_convertPropsToChatterFields
        [Action/params]
            props
        [Action/behavior]
            [Chatter/activityIds]
                @props
                .{Dict/get}
                    activityIds
            [Chatter/context]
                @props
                .{Dict/get}
                    context
            [Chatter/followerIds]
                @props
                .{Dict/get}
                    followerIds
            [Chatter/hasActivities]
                @props
                .{Dict/get}
                    hasActivities
            [Chatter/hasFollowers]
                @props
                .{Dict/get}
                    hasFollowers
            [Chatter/hasMessageList]
                @props
                .{Dict/get}
                    hasMessageList
            [Chatter/isAttachmentBoxVisibleInitially]
                @props
                .{Dict/get}
                    isAttachmentBoxVisibleInitially
            [Chatter/messageIds]
                @props
                .{Dict/get}
                    messageIds
            [Chatter/threadAttachmentCount]
                @props
                .{Dict/get}
                    threadAttachmentCount
            [Chatter/threadId]
                @props
                .{Dict/get}
                    threadId
            [Chatter/threadModel]
                @props
                .{Dict/get}
                    threadModel
`;
