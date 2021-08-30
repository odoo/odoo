/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            textual representations of shift previous/next operations are correctly mapped to right/left in LTR locale
        [Test/model]
            ChatWindowManagerComponent
        [Test/assertions]
            2
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/owlEnv]
                        [_t]
                            {Object/assign}
                                [0]
                                    {Record/insert}
                                        [Record/models]
                                            Function
                                        [Function/in]
                                            s
                                        [Function/out]
                                            @s
                                [1]
                                    [database]
                                        [parameters]
                                            [code]
                                                en_US
                                            [date_format]
                                                %m/%d/%Y
                                            [decimal_point]
                                                .
                                            [direction]
                                                rtl
                                            [grouping]
                                                []
                                            [thousands_sep]
                                                ,
                                            [time_format]
                                                %H:%M:%S
            @testEnv
            .{Record/insert}
                [0]
                    [Record/models]
                        mail.channel
                    [mail.channel/is_minimized]
                        true
                [1]
                    [Record/models]
                        mail.channel
                    [mail.channel/is_minimized]
                        true
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            @testEnv
            .{Record/insert}
                [Record/models]
                    ChatWindowManagerComponent
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/first}
                    .{ChatWindow/chatWindowHeaderComponents}
                    .{Collection/first}
                    .{ChatWindowHeaderComponent/commandShiftPrev}
                    .{web.Element/title}
                    .{=}
                        Shift right
                []
                    shift previous operation should have 'Shift right' as title in RTL locale
            {Test/assert}
                []
                    @testEnv
                    .{ChatWindowManager/chatWindows}
                    .{Collection/second}
                    .{ChatWindow/chatWindowHeaderComponents}
                    .{Collection/first}
                    .{ChatWindowHeaderComponent/commandShiftPrev}
                    .{web.Element/title}
                    .{=}
                        Shift left
                []
                    shift next operation should have 'Shift left' as title in RTL locale
`;
