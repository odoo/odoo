/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingInitializer/_loadMessageFailures
        [Action/params]
            record
                [type]
                    MessagingInitializer
        [Action/behavior]
            :data
                {Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    rpc
                .{Function/call}
                    [0]
                        [route]
                            /mail/load_message_failures
                    [1]
                        [shadow]
                            true
            {MessagingInitializer/_initMailFailures}
                [0]
                    @record
                [1]
                    @data
`;
