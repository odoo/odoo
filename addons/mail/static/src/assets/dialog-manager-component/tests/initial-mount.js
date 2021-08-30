/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            initial mount
        [Test/model]
            DialogManagerComponent
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
                    should have dialog manager
`;
