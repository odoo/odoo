/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Performs the rpc to leave the rtc call of the channel.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/performRpcLeaveCall
        [Action/params]
            record
                [type]
                    Thread
        [Action/behavior]
            {Record/doAsync}
                [0]
                    @record
                [1]
                    @env
                    .{Env/owlEnv}
                    .{Dict/get}
                        services
                    .{Dict/get}
                        rpc
                    .{Function/call}
                        [0]
                            [route]
                                /mail/rtc/channel/leave_call
                            [params]
                                [channel_id]
                                    @record
                                    .{Thread/id}
                        [1]
                            [shadow]
                                true
`;
