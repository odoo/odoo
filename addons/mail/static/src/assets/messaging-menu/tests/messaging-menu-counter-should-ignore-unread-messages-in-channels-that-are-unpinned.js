/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            messaging menu counter should ignore unread messages in channels that are unpinned
        [Test/model]
            MessagingMenu
        [Test/assertions]
            1
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @test
                    .{Test/data}
            @testEnv
            .{Record/insert}
                [Record/models]
                    Thread
                [Thread/id]
                    31
                [Thread/isServerPinned]
                    false
                [Thread/model]
                    mail.channel
                [Thread/serverMessageUnreadCounter]
                    1
            {Test/assert}
                [0]
                    @testEnv
                    .{MessagingMenu/counter}
                    .{=}
                        0
                [1]
                    messaging menu counter should ignore unread messages in channels that are unpinned
`;
