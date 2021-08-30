/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            link: should link a record to an empty x2many field
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
            :task
                @testEnv
                .{Record/insert}
                    [Record/models]
                        TestTask
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
                            @task
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
                    the record should be linked
            {Test/assert}
                []
                    @task
                    .{TestTask/responsible}
                    .{=}
                        @contact
                []
                    the inverse relation should be set as well
`;
