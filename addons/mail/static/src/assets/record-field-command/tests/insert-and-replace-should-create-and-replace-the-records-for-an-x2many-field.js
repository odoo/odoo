/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            insertAndReplace: should create and replace the records for an x2many field
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
                        1
                []
                    should have 1 record
            {Test/assert}
                []
                    @contact
                    .{TestContact/tasks}
                    .{Collection/first}
                    .{=}
                        @task20
                []
                    task should be replaced by the new record
            {Test/assert}
                []
                    @task20
                    .{TestTask/responsible}
                    .{=}
                        @contact
                []
                    the inverse relation should be set
            {Test/assert}
                []
                    @task10
                    .{TestTask/responsible}
                    .{=}
                        undefined
                []
                    the original relation should be dropped
`;
