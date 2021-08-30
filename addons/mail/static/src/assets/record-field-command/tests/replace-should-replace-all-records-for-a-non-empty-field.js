/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            replace: should replace all records for a non-empty field
        [Test/model]
            RecordFieldCommand
        [Test/assertions]
            5
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
                            []
                                [Record/models]
                                    TestTask
                                [TestTask/id]
                                    10
                            []
                                [Record/models]
                                    TestTask
                                [TestTask/id]
                                    20
            :task10
                @testEnv
                .{Record/findById}
                    [TestTask/id]
                        10
            :task20
                @testEnv
                .{Record/findById}
                    [TestTask/id]
                        20
            :task30
                @testEnv
                .{Record/insert}
                    [Record/models]
                        TestTask
                    [TestTask/id]
                        30
            @testEnv
            .{Record/update}
                [0]
                    @contact
                [1]
                    [TestContact/tasks]
                        @task30
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
                        @task30
                []
                    should be replaced with the new record
            {Test/assert}
                []
                    @task30
                    .{TestTask/responsible}
                    .{=}
                        @contact
                []
                    the inverse relation should be set as well
            {Test/assert}
                []
                    @task10
                    .{TestTask/responsible}
                    .{=}
                        undefined
                []
                    the original relation should be dropped
            {Test/assert}
                []
                    @task20
                    .{TestTask/responsible}
                    .{=}
                        undefined
                []
                    the original relation should be dropped
`;
