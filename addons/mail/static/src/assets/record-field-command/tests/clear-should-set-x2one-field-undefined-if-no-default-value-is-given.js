/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            clear: should set x2one field undefined if no default value is given
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
                    [TestContact/address]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                TestAddress
                            [TestAddress/id]
                                20
            :address
                @testEnv
                .{Record/findById}
                    [TestAddress/id]
                        20
            @testEnv
            .{Record/update}
                [0]
                    @contact
                [1]
                    [TestContact/address]
                        @testEnv
                        .{Record/empty}
            {Test/assert}
                []
                    @contact
                    .{TestContact/address}
                    .{=}
                        undefined
                []
                    clear: should set x2one field undefined
            {Test/assert}
                []
                    @address
                    .{TestAddress/contact}
                    .{=}
                        undefined
                []
                    the inverse relation should be cleared as well
`;
