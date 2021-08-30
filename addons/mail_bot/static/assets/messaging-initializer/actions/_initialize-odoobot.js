/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingInitializer/_initializeOdoobot
        [Action/feature]
            mail_bot
        [Action/params]
            messagingInitializer
                [type]
                    MessagingInitializer
        [Action/behavior]
            :data
                {Record/doAsync}
                    [0]
                        @messagingInitializer
                    [1]
                        @env
                        .{Env/owlEnv}
                        .{Dict/get}
                            services
                        .{Dict/get}
                            rpc
                        .{Function/call}
                            [model]
                                mail.channel
                            [method]
                                init_odoobot
            {if}
                @data
                .{isFalsy}
            .{then}
                {break}
            {Record/update}
                [0]
                    @env
                    .{Env/owlEnv}
                    .{Dict/get}
                        session
                [1]
                    [odoobot_initialized]
                        true
`;
