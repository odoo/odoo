/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            channel - counter: should not have a counter if the category is unfolded and without needaction messages
        [Test/model]
            DiscussSidebarCategoryComponent
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
                [mail.channel/id]
                    20
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
            .{Discuss/open}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/categoryChannel}
                    .{DiscussSidebarCategory/counter}
                    .{isFalsy}
                []
                    should not have a counter if the category is unfolded and without unread messages
`;