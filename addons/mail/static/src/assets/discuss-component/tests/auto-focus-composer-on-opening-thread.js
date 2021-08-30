/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            auto-focus composer on opening thread
        [Test/model]
            DiscussComponent
        [Test/assertions]
            11
        [Test/scenario]
            :testEnv
                {record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [0]
                    {Dev/comment}
                        channel expected to be found in the sidebar
                    [Record/models]
                        mail.channel
                    [mail.channel/id]
                        20
                        {Dev/comment}
                            random unique id, will be referenced in the test
                    [mail.channel/name]
                        General
                        {Dev/comment}
                            random name, will be asserted in the test
                [1]
                    {Dev/comment}
                        chat expected to be found in the sidebar
                    [Record/models]
                        mail.channel
                    [mail.channel/channel_type]
                        chat
                        {Dev/comment}
                            testing a chat is the goal of the test
                    [mail.channel/id]
                        10
                        {Dev/comment}
                            random unique id, will be referenced in the test
                    [mail.channel/members]
                        [0]
                            @record
                            .{Test/data}
                            .{Data/currentPartnerId}
                        [1]
                            7
                            {Dev/comment}
                                expected partners
                    [mail.channel/public]
                        private
                        {Dev/comment}
                            expected value for testing a chat
                [2]
                    {Dev/comment}
                        expected correspondent, with a random unique id that will be used to link
                        partner to chat and a random name that will be asserted in the test
                    [Record/models]
                        res.partner
                    [res.partner/id]
                        7
                    [res.partner/name]
                        Demo User
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
                            inbox
                        [Thread/model]
                            mail.box
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                [2]
                    should have mailbox 'Inbox' in the sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{=}
                        @testEnv
                        .{Record/findById}
                            [Thread/id]
                                inbox
                            [Thread/model]
                                mail.box
                []
                    mailbox 'Inbox' should be active initially
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
                    should have channel 'General' in the sidebar
            {Test/assert}
                []
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            10
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have chat 'Demo User' in the sidebar

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            20
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
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
                    channel 'General' should become active after selecting it from the sidebar
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
                    there should be a composer when active thread of discuss is channel 'General'
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                    .{=}
                        {web.Browser/document}
                        .{web.Document/activeElement}
                []
                    composer of channel 'General' should be automatically focused on opening

            @testEnv
            .{UI/blur}
                @testEnv
                .{Discuss/thread}
                .{Thread/composer}
                .{Composer/composerTextInputComponents}
                .{Collection/first}
                .{ComposerTextInputComponent/textarea}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{ComposerTextInputComponent/textarea}
                    .{!=}
                        @testEnv
                        .{web.Browser/document}
                        .{web.Document/activeElement}
                []
                    composer of channel 'General' should no longer focused on click away

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Record/findById}
                        [Thread/id]
                            10
                        [Thread/model]
                            mail.channel
                    .{Thread/discussSidebarCategoryItemComponents}
                    .{Collection/first}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{=}
                        @testEnv
                        .{Record/findById}
                            [Thread/id]
                                10
                            [Thread/model]
                                mail.channel
                []
                    chat 'Demo User' should become active after selecting it from the sidebar
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
                    there should be a composer when active thread of discuss is chat 'Demo User'
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{Thread/composer}
                    .{Composer/composerTextInputComponents}
                    .{Collection/first}
                    .{=}
                        @testEnv
                        .{web.Browser/document}
                        .{web.Document/activeElement}
                []
                    composer of chat 'Demo User' should be automatically focused on opening
`;
