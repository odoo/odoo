/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            set: should set a value for attribute field
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
                        20
            {Test/assert}
                []
                    @task
                    .{TestTask/difficulty}
                    .{=}
                        20
                []
                    set: should set a value for attribute field
`;
