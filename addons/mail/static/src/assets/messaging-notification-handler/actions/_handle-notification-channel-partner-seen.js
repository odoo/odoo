/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Called when a channel has been seen, and the server responds with the
        last message seen. Useful in order to track last message seen.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotificationChannelPartnerSeen
        [Action/params]
            notificationHandler
                [type]
                    MessagingNotificationHandler
            channel_id
                [type]
                    Integer
                [as]
                    channelId
            last_message_id
                [type]
                    Integer
            partner_id
                [type]
                    Integer
            guest_id
                [type]
                    Integer
        [Action/behavior]
            :channel
                {Record/findById}
                    [Thread/id]
                        @channelId
                    [Thread/model]
                        mail.channel
            {if}
                @channel
                .{isFalsy}
            .{then}
                {Dev/comment}
                    for example seen from another browser, the current one
                    has no knowledge of the channel
                {break}
            :lastMessage
                {Record/insert}
                    [Record/models]
                        Message
                    [Message/id]
                        last_message_id
            {Dev/comment}
                restrict computation of seen indicator for "non-channel"
                channels for performance reasons
            :shouldComputeSeenIndicators
                @channel
                .{Thread/channelType}
                .{!=}
                    channel
            {if}
                @shouldComputeSeenIndicators
            .{then}
                {Record/insert}
                    [Record/models]
                        ThreadPartnerSeenInfo
                    [ThreadPartnerSeenInfo/lastSeenMessage]
                        @lastMessage
                    [ThreadPartnerSeenInfo/partner]
                        {Record/insert}
                            [Record/models]
                                Partner
                            [Partner/id]
                                @partner_id
                    [ThreadPartnerSeenInfo/thread]
                        @channel
                {Record/insert}
                    [Record/models]
                        MessageSeenIndicator
                    [MessageSeenIndicator/message]
                        @lastMessage
                    [MessageSeenIndicator/thread]
                        @channel
            {if}
                {Env/currentPartner}
                .{&}
                    {Env/currentPartner}
                    .{Partner/id}
                    .{=}
                        @partner_id
            .{then}
                {Record/update}
                    [0]
                        @channel
                    [1]
                        [Thread/lastSeenByCurrentPartnerMessageId]
                            @last_message_id
                        [Thread/pendingSeenMessageId]
                            undefined
            {if}
                @shouldComputeSeenIndicators
            .{then}
                {Dev/comment}
                    FIXME force the computing of thread values (cf task-2261221)
                {Thread/computeLastCurrentPartnerMessageSeenByEveryone}
                    @channel
                {Dev/comment}
                    FIXME force the computing of message values (cf task-2261221)
                {MessageSeenIndicator/recomputeSeenValues}
                    @channel
`;
