/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            messaging not created
        [Test/model]
            ChatWindowManagerComponent
        [Test/isTechnical]
            true
        [Test/assertions]
            2
        [Test/scenario]
            {Dev/comment}
                Creation of messaging in env is async due to generation of models being
                async. Generation of models is async because it requires parsing of all
                JS modules that contain pieces of model definitions.

                Time of having no messaging is very short, almost imperceptible by user
                on UI, but the display should not crash during this critical time period.
            :def
                {Record/insert}
                    [Record/models]
                        Deferred
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/beforeGenerateModels]
                        @def
                    [Env/waitUntilMessagingCondition]
                        none
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
                    ChatWindowManagerComponent
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have chat window manager even when messaging is not yet created

            {Dev/comment}
                simulate messaging being created
            {Deferred/resolve}
                @def
            {Utils/nextAnimationFrame}
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindowManagerComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should still contain chat window manager after messaging has been created
`;
