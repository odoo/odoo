/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            multiple attribute commands combination
        [Test/model]
            RecordFieldCommand
        [Test/assertions]
            1
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            :task
                @testEnv
                .{Record/insert}
                    [Record/models]
                        TestTask
                    [TestTask/difficulty]
                        5
                    [TestTask/id]
                        10
            @testEnv
            .{Record/update}
                [0]
                    @task
                [1]
                    [TestTask/difficulty]
                        {Record/insert}
                            [Record/models]
                                Collection
                            [0]
                                20
                            [1]
                                @testEnv
                                .{Field/add}
                                    16
                            [2]
                                @testEnv
                                .{Field/remove}
                                    8
            {Test/assert}
                []
                    @task
                    .{TestTask/difficulty}
                    .{=}
                        20
                        .{+}
                            16
                        .{-}
                            8
                []
                    multiple attribute commands combination should work as expected
`;
