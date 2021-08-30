/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            insert: should create and add a new record for an x2many field
        [Test/model]
            RecordFieldCommand
        [Test/assertions]
            4
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
            :task10
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
                            .{Record/insert}
                                [Record/models]
                                    TestTask
                                [TestTask/id]
                                    20
            :task20
                @testEnv
                .{Record/findById}
                    [TestTask/id]
                        20
            {Test/assert}
                []
                    @contact
                    .{TestContact/tasks}
                    .{Collection/length}
                    .{=}
                        2
                []
                    should have 2 records
            {Test/assert}
                []
                    @contact
                    .{TestContact/tasks}
                    .{Collection/first}
                    .{=}
                        @task10
                []
                    the original record should be kept
            {Test/assert}
                []
                    @contact
                    .{TestContact/tasks}
                    .{Collection/second}
                    .{=}
                        @task20
                []
                    new record should be added
            {Test/assert}
                []
                    @task20
                    .{TestTask/responsible}
                    .{=}
                        @contact
                []
                    the inverse relation should be set as well
`;
