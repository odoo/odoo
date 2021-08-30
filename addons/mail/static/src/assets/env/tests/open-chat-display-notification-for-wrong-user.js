/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Test
        [Test/name]
            openChat: display notification for wrong user
        [Test/model]
            Env
        [Test/assertions]
            2
        [Test/scenario]
            :testEnv
                {Record/insert}
                    [Record/models]
                        Env
                    [Env/owlEnv]
                        [services]
                            [notification]
                                [notif]
                                    {Record/insert}
                                        [Record/models]
                                            Function
                                        [Function/in]
                                            notification
                                        [Function/out]
                                            {Test/assert}
                                                [0]
                                                    @record
                                                [1]
                                                    true
                                                [2]
                                                    should display a toast notification after failing to open chat
                                            {Test/assert}
                                            .{Rect/test}
                                                [0]
                                                    @record
                                                [1]
                                                    @notification
                                                    .{Dict/get}
                                                        message
                                                    .{=}
                                                        You can only chat with existing users.
                                                [2]
                                                    should display the correct information in the notification
            @testEnv
            .{Record/insert}
                [Record/models]
                    Server
                [Server/data]
                    @record
                    .{Test/data}
            {Dev/comment}
                user id not in test.data
            @testEnv
            .{Env/openChat}
                [userId]
                    14
`;
