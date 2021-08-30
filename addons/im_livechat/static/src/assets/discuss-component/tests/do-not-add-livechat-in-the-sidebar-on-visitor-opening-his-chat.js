/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            do not add livechat in the sidebar on visitor opening his chat
        [Test/feature]
            im_livechat
        [Test/model]
            DiscussComponent
        [Test/assertions]
            2
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                []
                    [Record/models]
                        res.users
                    [res.users/id]
                        @record
                        .{Test/data}
                        .{Data/currentUserId}
                    [res.users/im_status]
                        online
                []
                    [Record/models]
                        im_livechat.channel
                    [im_livechat.channel/id]
                        10
                    [im_livechat.user_ids]
                        @record
                        .{Test/data}
                        .{Data/currentUserId}
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
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryLivechat}
                    .{isFalsy}
                []
                    should not have any livechat in the sidebar initially

            {Dev/comment}
                simulate livechat visitor opening his chat
            @testEnv
            .{Env/owlEnv}
            .{Dict/get}
                services
            .{Dict/get}
                rpc
            .{Function/call}
                [route]
                    /im_livechat/get_session
                [params]
                    [context]
                        [mockedUserId]
                            false
                    [channel_id]
                        10
            {Utils/nextAnimationFrame}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryLivechat}
                    .{isFalsy}
                []
                    should still not have any livechat in the sidebar after visitor opened his chat
`;
