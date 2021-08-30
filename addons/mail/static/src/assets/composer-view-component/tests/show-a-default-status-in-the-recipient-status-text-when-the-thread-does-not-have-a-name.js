/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            show a default status in the recipient status text when the thread does not have a name
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
                    .{Composer/componentComponents}
                    .{Collection/first}
                    .{ComposerViewComponent/followers}
                    .{web.Element/textContent}
                    .{=}
                        To: Followers of this document
                []
                    Composer should display "To: Followers of this document" if the thread as no name.
`;
