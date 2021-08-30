/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            mobile: select another mailbox
        [Test/model]
            DiscussComponent
        [Test/assertions]
            7
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/owlEnv]
                        [browser]
                            [innerHeight]
                                640
                            [innerWidth]
                                360
                        [device]
                            [isMobile]
                                true
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
                    .{Collection/length}
                    .{=}
                        1
                []
                    should display discuss initially
            {Test/assert}
                []
                    @testEnv
                    .{Device/isMobile}
                []
                    discuss should be opened in mobile mode
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                []
                    discuss should display a thread initially
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{=}
                        @testEnv
                        .{Env/inbox}
                []
                    inbox mailbox should be opened initially
            {Test/containsOnce}
                []
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            DiscussMobileMailboxSelectionComponent
                    .{Collection/first}
                    .{DiscussMobileMailboxSelectionComponent/button}
                    .{Collection/find}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                button
                            [Function/out]
                                @button
                                .{Button/mailbox}
                                .{=}
                                    @testEnv
                                    .{Env/starred}
                []
                    should have a button to open starred mailbox

            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @testEnv
                    .{Record/all}
                        [Record/models]
                            DiscussMobileMailboxSelectionComponent
                    .{Collection/first}
                    .{DiscussMobileMailboxSelectionComponent/button}
                    .{Collection/find}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                button
                            [Function/out]
                                @button
                                .{Button/mailbox}
                                .{=}
                                    @testEnv
                                    .{Env/starred}
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                []
                    discuss should still have a thread after clicking on starred mailbox
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/thread}
                    .{=}
                        @testEnv
                        .{Env/starred}
                []
                    starred mailbox should be opened after clicking on it
`;
