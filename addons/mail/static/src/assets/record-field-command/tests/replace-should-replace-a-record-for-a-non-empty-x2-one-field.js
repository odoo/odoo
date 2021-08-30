/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            replace: should replace a record for a non-empty x2one field
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
                    [TestContact/address]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                TestAddress
                            [TestAddress/id]
                                10
                    [TestContact/id]
                        10
            :address10
                @testEnv
                .{Record/findById}
                    [TestAddress/id]
                        10
            :address20
                @testEnv
                .{Record/insert}
                    [Record/models]
                        TestAddress
                    [TestAddress/id]
                        20
            @testEnv
            .{Record/update}
                [0]
                    @contact
                [1]
                    [TestContact/address]
                        @address20
            {Test/assert}
                []
                    @contact
                    .{TestContact/address}
                    .{=}
                        @address20
                []
                    replace: should replace a record for a non-empty x2one field
            {Test/assert}
                []
                    @address20
                    .{TestAddress/contact}
                    .{=}
                        @contact
                []
                    the inverse relation should be set as well
            {Test/assert}
                []
                    @address10
                    .{TestAddress/contact}
                    .{=}
                        undefined
                []
                    the original relation should be dropped
`;
