/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            livechat: public website visitor is typing
        [Test/feature]
            im_livechat
        [Test/model]
            ThreadIconComponent
        [Test/assertions]
            4
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
                    ThreadIconComponent
                [ThreadIconComponent/thread]
                    @thread
            {Test/assert}
                []
                    @thread
                    .{Thread/threadIconComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have thread icon
            {Test/assert}
                []
                    @thread
                    .{Thread/threadIconComponents}
                    .{Collection/first}
                    .{ThreadIconComponent/iconLivechat}
                    .{web.Element/class}
                    .{String/includes}
                        fa-comments
                []
                    should have default livechat icon

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
                    .{Thread/threadIconComponents}
                    .{Collection/first}
                    .{ThreadIconComponent/typing}
                []
                    should have thread icon with visitor currently typing
            {Test/assert}
                []
                    @thread
                    .{Thread/threadIconComponents}
                    .{Collection/first}
                    .{ThreadIconComponent/typing}
                    .{web.Element/title}
                    .{=}
                        Visitor 20 is typing...
                []
                    title of icon should tell visitor is currently typing
`;
