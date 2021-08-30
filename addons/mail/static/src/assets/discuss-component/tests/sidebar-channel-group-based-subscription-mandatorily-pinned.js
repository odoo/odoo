/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            sidebar: channel group_based_subscription: mandatorily pinned
        [Test/model]
            DiscussComponent
        [Test/assertions]
            2
        [Test/scenario]
            {Dev/comment}
                FIXME: The following is admittedly odd.
                Fixing it should entail a deeper reflexion on the
                group_based_subscription and is_pinned functionalities,
                especially in python.
                task-2284357
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                {Dev/comment}
                    channel that is expected to be found in the sidebar
                [Record/models]
                    mail.channel
                [mail.channel/group_based_subscription]
                    true
                    {Dev/comment}
                        expected value for this test
                [mail.channel/id]
                    20
                    {Dev/comment}
                        random unique id, will be referenced in the test
                [mail.channel/is_pinned]
                    false
                    {Dev/comment}
                        expected value for this test
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
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    the channel #General is in discuss sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/commandLeave}
                    .{isFalsy}
                []
                    the group_based_subscription channel is not unpinnable
`;
