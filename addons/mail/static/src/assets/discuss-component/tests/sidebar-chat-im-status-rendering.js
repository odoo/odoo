/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            sidebar: chat im_status rendering
        [Test/model]
            DiscussComponent
        [Test/assertions]
            7
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                {Dev/comment}
                    chats expected to be found in the sidebar
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/channel_type]
                        chat
                        {Dev/comment}
                            testing a chat is the goal of the test
                    [mail.channel/id]
                        11
                        {Dev/comment}
                            random unique id, will be referenced in the test
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
                    [Record/models]
                        mail.channel
                    [mail.channel/channel_type]
                        chat
                        {Dev/comment}
                            testing a chat is the goal of the test
                    [mail.channel/id]
                        12
                        {Dev/comment}
                            random unique id, will be referenced in the test
                    [mail.channel/members]
                        {Dev/comment}
                            expected partners
                        [0]
                            @record
                            .{Test/data}
                            .{Data/currentPartnerId}
                        [1]
                            102
                    [mail.channel/public]
                        private
                        {Dev/comment}
                            expected value for testing a chat
                [2]
                    [Record/models]
                        mail.channel
                    [mail.channel/channel_type]
                        chat
                        {Dev/comment}
                            testing a chat is the goal of the test
                    [mail.channel/id]
                        13
                        {Dev/comment}
                            random unique id, will be referenced in the test
                    [mail.channel/members]
                        {Dev/comment}
                            expected partners
                        [0]
                            @record
                            .{Test/data}
                            .{Data/currentPartnerId}
                        [1]
                            103
                    [mail.channel/public]
                        private
                        {Dev/comment}
                            expected value for testing a chat
                [3]
                    {Dev/comment}
                        expected correspondent, with a random unique id that
                        will be used to link partner to chat, and various
                        im_status values to assert
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        101
                    [res.partner/im_status]
                        offline
                    [res.partner/name]
                        Partner1
                [4]
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        102
                    [res.partner/im_status]
                        online
                    [res.partner/name]
                        Partner2
                [5]
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        103
                    [res.partner/im_status]
                        away
                    [res.partner/name]
                        Partner3
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
                    .{Collection/length}
                    .{=}
                        3
                []
                    should have 3 chat items
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            11
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have Partner1 (Id 11)
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            12
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have Partner2 (Id 12)
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            13
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have Partner3 (Id 13)
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            11
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
                    .{DiscussSidebarCategoryItemComponent/threadIcon}
                    .{ThreadIconComponent/offline}
                []
                    chat1 should have offline icon
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            12
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{DiscussSidebarCategoryItemComponent/threadIcon}
                    .{ThreadIconComponent/online}
                []
                    chat2 should have online icon
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            13
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{DiscussSidebarCategoryItemComponent/threadIcon}
                    .{ThreadIconComponent/away}
                []
                    chat3 should have away icon
`;
