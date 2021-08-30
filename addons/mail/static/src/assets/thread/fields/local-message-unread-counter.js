/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Local value of message unread counter, that means it is based on initial server value and
        updated with interface updates.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            localMessageUnreadCounter
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/compute]
            {if}
                @record
                .{Thread/model}
                .{!=}
                    mail.channel
            .{then}
                {Dev/comment}
                    unread counter only makes sense on channels
                {Record/empty}
                {break}
            {Dev/comment}
                By default trust the server up to the last message it used
                because it's not possible to do better.
            :baseCounter
                @record
                .{Thread/serverMessageUnreadCounter}
            :countFromId
                {if}
                    @record
                    .{Thread/serverLastMessage}
                .{then}
                    @record
                    .{Thread/serverLastMessage}
                    .{Message/id}
                .{else}
                    0
            {Dev/comment}
                But if the client knows the last seen message that the server
                returned (and by assumption all the messages that come after),
                the counter can be computed fully locally, ignoring potentially
                obsolete values from the server.
            {if}
                @record
                .{Thread/orderedMessages}
                .{Collection/first}
                .{&}
                    @record
                    .{Thread/lastSeenByCurrentPartnerMessageId}
                .{&}
                    @record
                    .{Thread/lastSeenByCurrentPartnerMessageId}
                    .{>=}
                        @record
                        .{Thread/orderedMessages}
                        .{Collection/first}
                        .{Message/id}
            .{then}
                :baseCounter
                    0
                :countFromId
                    @record
                    .{Thread/lastSeenByCurrentPartnerMessageId}
            {Dev/comment}
                Include all the messages that are known locally but the server
                didn't take into account.
            @record
            .{Thread/orderedMessages}
            .{Collection/reduce}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        acc
                        item
                    [Function/out]
                        {if}
                            @item
                            .{Message/id}
                            <=
                            @countFromId
                        .{then}
                            @acc
                        .{else}
                            @acc
                            .{+}
                                1
                @baseCounter
`;
