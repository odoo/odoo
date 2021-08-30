/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            sidebar: basic channel rendering
        [Test/model]
            DiscussComponent
        [Test/assertions]
            12
        [Test/scenario]
            {Dev/comment}
                channel expected to be found in the sidebar,
                with a random unique id and name that
                will be referenced in the test
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    mail.channel
                [mail.channel/id]
                    20
                [mail.channel/name]
                    General
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
                    .{DiscussSidebarComponent/itemChannel}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have one channel item
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/itemChannel}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/thread}
                    .{=}
                        @testEnv
                        .{Record/findById}
                            [Thread/id]
                                20
                            [Thread/model]
                                mail.channel
                []
                    should have channel with Id 20
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{!=}
                        @testEnv
                        .{Record/findById}
                            [Thread/id]
                                20
                            [Thread/model]
                                mail.channel
                []
                    should not be active by default
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/itemChannel}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/name}
                []
                    should have a name
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/itemChannel}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/name}
                    .{web.Element/textContent}
                    .{=}
                        General
                []
                    should have name value
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/itemChannel}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/commands}
                []
                    should have commands
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/itemChannel}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/command}
                    .{Collection/length}
                    .{=}
                        2
                []
                    should have 2 commands
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/itemChannel}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/commandSettings}
                []
                    should have 'settings' command
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/itemChannel}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/commandLeave}
                []
                    should have 'leave' command
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/itemChannel}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/counter}
                []
                    should have a counter when equals 0 (default value)

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/itemChannel}
                    .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{=}
                        @testEnv
                        .{Record/findById}
                            [Thread/id]
                                20
                            [Thread/model]
                                mail.channel
                []
                    channel should become active
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/composerViewComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have composer section inside thread content (can post message in channel)
`;
