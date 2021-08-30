/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            sidebar: public/private channel rendering
        [Test/model]
            DiscussComponent
        [Test/assertions]
            5
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                {Dev/comment}
                    channels that are expected to be found in the sidebar
                    (one public, one private) with random unique id and name
                    that will be referenced in the test
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        100
                    [mail.channel/name]
                        channel1
                    [mail.channel/public]
                        public
                [1]
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        101
                    [mail.channel/name]
                        channel2
                    [mail.channel/public]
                        private
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
                        2
                []
                    should have 2 channel items
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            100
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have channel1 (Id 100)
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            101
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have channel2 (Id 101)
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            100
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/threadIcon}
                    .{ThreadIconComponent/channelPublic}
                []
                    channel1 (public) should have globe icon
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            101
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/threadIcon}
                    .{ThreadIconComponent/channelPrivate}
                []
                    channel2 (private) has lock icon
`;
