/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Mark the specified conversation as read/seen.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/markAsSeen
        [Action/params]
            thread
                [type]
                    Thread
            message
                [type]
                    Message
                [description]
                    the message to be considered as last seen
        [Action/behavior]
            {if}
                {Env/currentGuest}
            .{then}
                {break}
            {if}
                @thread
                .{Thread/model}
                .{!=}
                    mail.channel
            .{then}
                {break}
            {if}
                @thread
                .{Thread/pendingSeenMessageId}
                .{&}
                    @message
                    .{Message/id}
                    .{<=}
                        @thread
                        .{Thread/pendingSeenMessageId}
            .{then}
                {break}
            {if}
                @thread
                .{Thread/lastSeenByCurrentPartnerMessageId}
                .{&}
                    @message
                    .{Message/id}
                    .{<=}
                        @thread
                        .{Thread/lastSeenByCurrentPartnerMessageId}
            .{then}
                {break}
            {Record/update}
                [0]
                    @thread
                [1]
                    [Thread/pendingSeenMessageId]
                        @message
                        .{Message/id}
            {Thread/performRpcChannelSeen}
                [id]
                    @thread
                    .{Thread/id}
                [lastMessageId]
                    @message
                    .{Message/id}
`;
