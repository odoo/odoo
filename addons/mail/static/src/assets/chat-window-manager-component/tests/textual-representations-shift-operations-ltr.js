/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            textual representations of shift previous/next operations are correctly mapped to left/right in LTR locale
        [Test/model]
            ChatWindowManagerComponent
        [Test/assertions]
            2
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    mail.channel
                [mail.channel/is_minimized]
                    true
                [mail.channel/is_minimized]
                    true
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @recod
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
                        Shift left
                []
                    shift previous operation should be have 'Shift left' as title in LTR locale
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
                        Shift right
                []
                    shift next operation should have 'Shift right' as title in LTR locale
`;
