/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            insert: should update existing records for an x2many field
        [Test/model]
            RecordFieldCommand
        [Test/assertions]
            3
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            :contact
                @testEnv
                .{Record/insert}
                    [Record/models]
                        TestContact
                    [TestContact/id]
                        10
                    [TestContact/tasks]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                TestTask
                            [TestTask/id]
                                10
                            [TestTask/title]
                                task 10
            :task
                @testEnv
                .{Record/findById}
                    [TestTask/id]
                        10
            @testEnv
            .{Record/update}
                [0]
                    @contact
                [1]
                    [TestContact/tasks]
                        @testEnv
                        .{Field/add}
                            @testEnv
                            .{Recod/insert}
                                [Record/models]
                                    TestTask
                                [TestTask/id]
                                    10
                                [TestTask/title]
                                    task 10 updated
            {Test/assert}
                []
                    @contact
                    .{TestContact/tasks}
                    .{Collection/length}
                    .{=}
                        1
                []
                    should have 1 record
            {Test/assert}
                []
                    @contact
                    .{TestContact/tasks}
                    .{Collection/first}
                    .{=}
                        @task
                []
                    the original task should be kept
            {Test/assert}
                []
                    @task
                    .{TestTask/title}
                    .{=}
                        task 10 updated
                []
                    should update the existing record
`;
