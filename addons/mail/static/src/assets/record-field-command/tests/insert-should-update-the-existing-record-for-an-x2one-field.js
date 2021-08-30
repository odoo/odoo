/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            insert: should update the existing record for an x2one field
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
                .{Record/models}
                    [Record/models]
                        TestContact
                    [TestContact/address]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                TestAddress
                            [TestAddress/addressInfo]
                                address 10
                            [TestAddress/id]
                                10
                    [TestContact/id]
                        10
            :address10
                @testEnv
                .{Record/findById}
                    [TestAddress/id]
                        10
            @testEnv
            .{Record/update}
                [0]
                    @contact
                [1]
                    [TestContact/address]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                TestAddress
                            [TestAddress/addressInfo]
                                address 10 updated
                            [TestAddress/id]
                                10
            {Test/assert}
                []
                    @contact
                    .{TestContact/address}
                    .{=}
                        @address10
                []
                    insert: should not drop an existing record
            {Test/assert}
                []
                    @address10
                    .{TestAddress/addressInfo}
                    .{=}
                        address 10 updated
                []
                    insert: should update the existing record for a x2one field
`;
