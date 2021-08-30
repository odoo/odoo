/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            unlink: should unlink the specified record for x2many field
        [Test/model]
            RecordFieldCommand
        [Test/assertions]
            2
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
            @testEnv
            .{Record/update}
                [0]
                    @contact
                [1]
                    [TestContact/tasks]
                        @testEnv
                        .{Field/remove}
                            @task10
            {Test/assert}
                []
                    @contact
                    .{TestContact/tasks}
                    .{Collection/length}
                    .{=}
                        1
                    .{&}
                        @contact
                        .{TestContact/tasks}
                        .{Collection/includes}
                            @task2
                []
                    unlink: should unlink the specified record for x2many field
            {Test/assert}
                []
                    @task10
                    .{TestTask/responsible}
                    .{=}
                        undefined
                []
                    the original relation should be dropped as well
`;
