/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            invite button should be present on livechat
        [Test/feature]
            im_livechat
        [Test/model]
            DiscussComponent
        [Test/assertions]
            1
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
                    Visitor 11
                [mail.channel/channel_type]
                    livechat
                [mail.channel/id]
                    11
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
            @testEnv
            .{Record/insert}
                [Record/models]
                    DiscussComponent
            @testEnv
            .{Thread/open}
                @testEnv
                .{Record/findById}
                    [Thread/id]
                        11
                    [Thread/model]
                        mail.channel
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/threadViews}
                    .{Collection/first}
                    .{ThreadView/threadViewTopbar}
                    .{ThreadViewTopbar/threadViewTopbarComponents}
                    .{Collection/first}
                    .{ThreadViewTopbarComponent/inviteButton}
                []
                    Invite button should be visible in top bar when livechat is active thread
`;
