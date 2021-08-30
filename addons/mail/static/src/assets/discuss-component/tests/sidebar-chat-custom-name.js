/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            sidebar: chat custom name
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
                {Dev/comment}
                    chat expected to be found in the sidebar
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/channel_type]
                        chat
                        {Dev/comment}
                            testing a chat is the goal of the test
                    [mail.channel/custom_channel_name]
                        Marc
                        {Dev/comment}
                            testing a custom name is the goal of the test
                    [mail.channel/members]
                        {Dev/comment}
                            expected partners
                        [0]
                            @record
                            .{Test/data}
                            .{Data/currentPartnerId}
                        [1]
                            101
                    [mail.channel/public]
                        private
                        {Dev/comment}
                            expected value for testing a chat
                [1]
                    {Dev/comment}
                        expected correspondent, with a random unique id
                        that will be used to link partner to chat,
                        and a random name not used in the scope of this
                        test but set for consistency
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        101
                    [res.partner/name]
                        Marc Demo
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
                    .{DiscussSidebarComponent/itemChat}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/name}
                    .{web.Element/textContent}
                    .{=}
                        Marc
                []
                    chat should have custom name as name
`;
