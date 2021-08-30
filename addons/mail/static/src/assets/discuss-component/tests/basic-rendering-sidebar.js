/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            basic rendering: sidebar
        [Test/model]
            DiscussComponent
        [Test/assertions]
            18
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
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/sidebar}
                    .{DiscussSidebarComponent/category}
                    .{Collection/length}
                    .{=}
                        3
                []
                    should have 3 categories in sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/sidebar}
                    .{DiscussSidebarComponent/categoryMailbox}
                []
                    should have category 'Mailbox' in sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/sidebar}
                    .{DiscussSidebarComponent/categoryMailbox}
                    .{DiscussSidebarCategoryComponent/item}
                    .{Collection/length}
                    .{=}
                        3
                []
                    should have 3 mailbox items
            {Test/assert}
                []
                    @testEnv
                    .{Env/inbox}
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have inbox mailbox item
            {Test/assert}
                []
                    @testEnv
                    .{Env/starred}
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have starred mailbox item
            {Test/assert}
                []
                    @testEnv
                    .{Env/history}
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have history mailbox item
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/separator}
                    .{Collection/length}
                    .{=}
                        2
                []
                    should have 2 separators (separating 'Start a meeting' button, mailboxes and channels, but that's not tested)
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryChannel}
                []
                    should have category 'Channel' in sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryChannel}
                    .{DiscussSidebarCategoryComponent/header}
                []
                    should have header in channel category
            {Test/assert}
                @testEnv
                .{Discuss/discussSidebarComponents}
                .{Collection/first}
                .{DiscussSidebarComponent/categoryChannel}
                .{DiscussSidebarCategoryComponent/header}
                .{web.Element/textContent}
                .{=}
                    Channels
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryChannel}
                    .{DiscussSidebarCategoryComponent/list}
                []
                    channel category should list items
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryChannel}
                    .{DiscussSidebarCategoryComponent/item}
                    .{Collection/length}
                    .{=}
                        0
                []
                    channel category should have no item by default
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryChat}
                []
                    should have category 'Chat' in sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryChat}
                    .{DiscussSidebarCategoryComponent/header}
                []
                    chat category should have a header
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryChat}
                    .{DiscussSidebarCategoryComponent/title}
                []
                    should have title in chat header
            {Test/assert}
                @testEnv
                .{Discuss/discussSidebarComponents}
                .{Collection/first}
                .{DiscussSidebarComponent/categoryChat}
                .{DiscussSidebarCategoryComponent/title}
                .{web.Element/textContent}
                .{=}
                    Direct Messages
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryChat}
                    .{DiscussSidebarCategoryComponent/list}
                []
                    chat category should list items
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussSidebarComponents}
                    .{Collection/first}
                    .{DiscussSidebarComponent/categoryChat}
                    .{DiscussSidebarCategoryComponent/item}
                    .{Collection/length}
                    .{=}
                        0
                []
                    chat category should have no item by default
`;
