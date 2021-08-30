/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            inbox messages are never squashed
        [Test/model]
            DiscussComponent
        [Test/assertions]
            3
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [0]
                    [Record/models]
                        mail.message
                    [mail.message/author_id]
                        11
                        {Dev/comment}
                            must be same author as other message
                    [mail.message/body]
                        <p>body1</p>
                        {Dev/comment}
                            random body, set for consistency
                    [mail.message/date]
                        2019-04-20 10:00:00
                        {Dev/comment}
                            date must be within 1 min from other message
                    [mail.message/id]
                        100
                        {Dev/comment}
                            random unique id, will be referenced in the test
                    [mail.message/message_type]
                        comment
                        {Dev/comment}
                            must be a squash-able type-
                    [mail.message/model]
                        mail.channel
                        {Dev/comment}
                            to link message to channel
                    [mail.message/needaction]
                        true
                    [mail.message/needaction_partner_ids]
                        @record
                        .{Test/data}
                        .{Data/currentPartnerId}
                        {Dev/comment}
                            for consistency
                    [mail.message/res_id]
                        20
                        {Dev/comment}
                            id of related channel
                [1]
                    [Record/models]
                        mail.message
                    [mail.message/author_id]
                        11
                        {Dev/comment}
                            must be same author as other message
                    [mail.message/body]
                        <p>body2</p>
                        {Dev/comment}
                            random body, will be asserted in the test
                    [mail.message/date]
                        2019-04-20 10:00:30
                        {Dev/comment}
                            date must be within 1 min from other message
                    [mail.message/id]
                        101
                        {Dev/comment}
                            random unique id, will be referenced in the test
                    [mail.message/message_type]
                        comment
                        {Dev/comment}
                            must be a squash-able type
                    [mail.message/model]
                        mail.channel
                        {Dev/comment}
                            to link message to channel
                    [mail.message/needaction]
                        true
                    [mail.message/needaction_partner_ids]
                        @record
                        .{Test/data}
                        .{Data/currentPartnerId}
                        {Dev/comment}
                            for consistency
                    [mail.message/res_id]
                        20
                        {Dev/comment}
                            id of related channel
                [2]
                    [Record/models]
                        mail.notification
                    [mail.notification/mail_message_id]
                        100
                    [mail.notification/notification_status]
                        sent
                    [mail.notification/notification_type]
                        inbox
                    [mail.notification/res_partner_id]
                        @record
                        .{Test/data}
                        .{Data/currentPartnerId}
                [3]
                    [Record/models]
                        mail.notification
                    [mail.notification/mail_message_id]
                        101
                    [mail.notification/notification_status]
                        sent
                    [mail.notification/notification_type]
                        inbox
                    [mail.notification/res_partner_id]
                        @record
                        .{Test/data}
                        .{Data/currentPartnerId}
                [4]
                    {Dev/comment}
                        partner to be set as author, with a random unique
                        id that will be used to link message
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        11
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            @testEnv
            .{Record/insert}
                [Record/models]
                    DiscussComponent
            @testEnv
            .{Utils/waitUntilEvent}
                [eventName]
                    o-thread-view-hint-processed
                [message]
                    should wait until inbox displayed its messages
                [predicate]
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            hint
                            threadViewer
                        [Function/out]
                            @hint
                            .{Hint/type}
                            .{=}
                                messages-loaded
                            .{&}
                                @threadViewer
                                .{ThreadViewer/thread}
                                .{Thread/model}
                                .{=}
                                    mail.box
                            .{&}
                                @threadViewer
                                .{ThreadViewer/thread}
                                .{Thread/id}
                                .{=}
                                    inbox
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/cache}
                    .{ThreadCache/messages}
                    .{Collection/length}
                    .{=}
                        2
                []
                    should have 2 messages
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            100
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/isSquashed}
                    .{isFalsy}
                []
                    message 1 should not be squashed
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Message/id]
                            101
                    .{Message/messageComponents}
                    .{Collection/first}
                    .{MessageViewComponent/isSquashed}
                    .{isFalsy}
                []
                    message 2 should not be squashed
`;
