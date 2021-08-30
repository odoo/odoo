/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            clear: should set x2one field the default value
        [Test/model]
            RecordFieldCommand
        [Test/assertions]
            1
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
                    [TestContact/favorite]
                        @testEnv
                        .{Record/insert}
                            [Record/models]
                                TestHobby
                            [TestHobby/description]
                                pingpong
                    [TestContact/id]
                        10
            @testEnv
            .{Record/update}
                [0]
                    @contact
                [1]
                    [TestContact/favorite]
                        @testEnv
                        .{Record/empty}
            {Test/assert}
                []
                    @contact
                    .{TestHobby/description}
                    .{TestContact/favorite}
                    .{=}
                        football
                []
                    clear: should set x2one field default value
`;
