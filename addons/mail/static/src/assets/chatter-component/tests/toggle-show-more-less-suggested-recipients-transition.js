/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            more than 3 suggested recipients -> click "show more" -> "show less" button
        [Test/model]
            ChatterComponent
        [Test/assertions]
            1
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [0]
                    [Record/models]
                        res.fake
                    [res.fake/id]
                        10
                    [res.fake/partner_ids]
                        100
                        1000
                        1001
                        1002
                [1]
                    [Record/models]
                        res.partner
                    [res.partner/display_name]
                        John Jane
                    [res.partner/email]
                        john@jane.be
                    [res.partner/id]
                        100
                [2]
                    [Record/models]
                        res.partner
                    [res.partner/display_name]
                        Jack Jone
                    [res.partner/email]
                        jack@jone.be
                    [res.partner/id]
                        1000
                [3]
                    [Record/models]
                        res.partner
                    [res.partner/display_name]
                        jolly Roger
                    [res.partner/email]
                        Roger@skullflag.com
                    [res.partner/id]
                        1001
                [4]
                    [Record/models]
                        res.partner
                    [res.partner/display_name]
                        jack sparrow
                    [res.partner/email]
                        jsparrow@blackpearl.bb
                    [res.partner/id]
                        1002
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
                    ChatterContainerComponent
                [ChatterContainerComponent/threadId]
                    10
                [ChatterContainerComponent/threadModel]
                    res.fake
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @chatter
                    .{Chatter/chatterTopbarComponents}
                    .{Collection/first}
                    .{ChatterTopbarComponent/buttonSendMessage}
            @testEnv
            .{Component/afterNextRender}
                @testEnv
                .{UI/click}
                    @chatter
                    .{Chatter/thread}
                    .{Thread/composerSuggestedRecipientListComponents}
                    .{Collection/first}
                    .{ComposerSuggestedRecipientListComponent/showMore}
            {Test/assert}
                []
                    @chatter
                    .{Chatter/thread}
                    .{Thread/composerSuggestedRecipientListComponents}
                    .{Collection/first}
                    .{ComposerSuggestedRecipientListComponent/showLess}
                []
                    more than 3 suggested recipients -> click 'show more' -> 'show less' button
`;
