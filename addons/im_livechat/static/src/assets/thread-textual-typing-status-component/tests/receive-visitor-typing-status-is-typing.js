/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            receive visitor typing status "is typing"
        [Test/feature]
            im_livechat
        [Test/model]
            ThreadTextualTypingStatusComponent
        [Test/assertions]
            2
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    mail.channel
                [mail.channel/anonymous_name]
                    Visitor 20
                [mail.channel/channel_type]
                    livechat
                [mail.channel/id]
                    20
                [mail.channel/livechat_operator_id]
                    @record
                    .{Test/data}
                    .{Data/currentPartnerId}
                [mail.channel/members]
                    [0]
                        @record
                        .{Test/data}
                        .{Data/currentPartnerId}
                    [1]
                        @record
                        .{Test/data}
                        .{Data/publicPartnerId}
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            :thread
                @testEnv
                .{Record/findById}
                    [Thread/id]
                        20
                    [Thread/model]
                        mail.channel
            @testEnv
            .{Record/insert}
                [Record/models]
                    ThreadTextualTypingStatusComponent
                [ThreadTextualTypingStatusComponent/thread]
                    @thread
            {Test/assert}
                []
                    @thread
                    .{Thread/threadTextualTypingStatusComponents}
                    .{Collection/first}
                    .{ThreadTextualTypingStatusComponent/text}
                    .{web.Element/textContent}
                    .{=}
                        {String/empty}
                []
                    Should display no one is currently typing

            {Dev/comment}
                simulate receive typing notification from livechat visitor "is typing"
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    bus_service
                .{Dict/get}
                    trigger
                .{Function/call}
                    [0]
                        notification
                    [1]
                        [type]
                            mail.channel.partner/typing_status
                        [payload]
                            [channel_id]
                                20
                            [is_typing]
                                true
                            [partner_id]
                                {Env/publicPartners}
                                .{Collection/first}
                                .{Partner/id}
                            [partner_name]
                                {Env/publicPartners}
                                .{Collection/first}
                                .{Partner/name}
            {Test/assert}
                []
                    @thread
                    .{Thread/threadTextualTypingStatusComponents}
                    .{Collection/first}
                    .{ThreadTextualTypingStatusComponent/text}
                    .{web.Element/textContent}
                    .{=}
                        Visitor 20 is typing...
                []
                    Should display that visitor is typing
`;
