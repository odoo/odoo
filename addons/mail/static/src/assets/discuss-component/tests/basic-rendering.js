/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            basic rendering
        [Test/model]
            DiscussComponent
        [Test/assertions]
            3
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
                    .{Discuss/discussSidebarComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have a sidebar section
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{DiscussComponent/content}
                []
                    should have content section
            {Test/assert}
                []
                    @testEnv
                    .{Discuss/discussComponents}
                    .{Collection/first}
                    .{Discuss/thread}
                []
                    should have thread section inside content
`;
