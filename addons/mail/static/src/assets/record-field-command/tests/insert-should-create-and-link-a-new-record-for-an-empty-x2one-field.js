/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            insert: should create and link a new record for an empty x2one field
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
            @testEnv
            .{Record/update}
                [0]
                    @contact
                [1]
                    [TestContact/address]
                        @testEnv
                        .{Field/add}
                            @testEnv
                            .{Record/insert}
                                [Record/models]
                                    TestAddress
                                [TestAddress/id]
                                    10
            :address
                @testEnv
                .{Record/findById}
                    [TestAddress/id]
                        10
            {Test/assert}
                []
                    @contact
                    .{TestContact/address}
                    .{=}
                        @address
                []
                    insert: should create and link a record for an empty x2one field
            {Test/assert}
                []
                    @address
                    .{TestAddress/contact}
                    .{=}
                        @contact
                []
                    the inverse relation should be set as well
`;
