/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            show a thread name in the recipient status text
        [Test/model]
            ComposerViewComponent
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
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            :thread
                @testEnv
                .{Record/insert}
                    [Record/models]
                        Thread
                    [Thread/composer]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                Composer
                            [Composer/isLog]
                                false
                    [Thread/id]
                        20
                    [Thread/model]
                        res.partner
                    [Thread/name]
                        test name
            @testEnv
            .{Record/insert}
                [Record/models]
                    ComposerViewComponent
                [ComposerViewComponent/composer]
                    @thread
                    .{Thread/composer}
                [ComposerViewComponent/hasFollowers]
                    true
            {Test/assert}
                []
                    @thread
                    .{Thread/composer}
                    .{Composer/composerViewComponents}
                    .{Collection/first}
                    .{ComposerViewComponent/followers}
                    .{web.Element/textContent}
                    .{=}
                        To: Followers of "testname"
                []
                    basic rendering when sending a message to the followers and thread does have a name
`;
