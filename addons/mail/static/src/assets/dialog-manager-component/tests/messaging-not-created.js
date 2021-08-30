/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            messaging not created
        [Test/model]
            DialogManagerComponent
        [Test/isTechnical]
            true
        [Test/assertions]
            2
        [Test/scenario]
            :def
                {Record/insert}
                    [Record/models]
                        Deferred
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/beforeGenerateModels]
                        {Promise/await}
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
                    DialogManagerComponent
            {Test/assert}
                []
                    @testEnv
                    .{DialogManager/dialogManagerComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have dialog manager even when messaging is not yet created

            {Dev/comment}
                simulate messaging being created
            {Promise/resolve}
                @def
            {Utils/nextAnimationFrame}
            {Test/assert}
                []
                    @testEnv
                    .{DialogManager/dialogManagerComponents}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should still contain dialog manager after messaging has been created
`;
