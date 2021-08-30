/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            sidebar: add channel
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
                    .{DiscussSidebarComponent/channelCategory}
                    .{DiscussSidebarCategoryComponent/commandAdd}
                []
                    should be able to add channel from category
            {Test/assert}
                @testEnv
                .{Discuss/discussSidebarComponents}
                .{Collection/first}
                .{DiscussSidebarComponent/channelCategory}
                .{DiscussSidebarCategoryComponent/commandAdd}
                .{web.Element/title}
                .{=}
                    Add or join a channel

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/channelCategory}
                    .{DiscussSidebarCategoryComponent/commandAdd}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/channelCategory}
                    .{DiscussSidebarCategoryComponent/addingItem}
                []
                    should have item to add a new channel
`;
