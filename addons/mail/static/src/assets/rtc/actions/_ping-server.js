/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Pings the server to ensure this session is kept alive.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_pingServer
        [Action/params]
            record
                [type]
                    Rtc
        [Action/behavior]
            :channel
                @record
                .{Rtc/channel}
            :res
                @env
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    rpc
                .{Function/call}
                    [0]
                        [route]
                            /mail/channel/ping
                        [params]
                            [channel_id]
                                @channel
                                .{Thread/id}
                            [check_rtc_session_ids]
                                @channel
                                .{Thread/rtcSessions}
                                .{Collection/map}
                                    {Record/insert}
                                        [Record/models]
                                            Function
                                        [Function/in]
                                            item
                                        [Function/out]
                                            @item
                                            .{RtcSession/id}
                            [rtc_session_id]
                                @record
                                .{Rtc/currentRtcSession}
                                .{RtcSession/id}
                    [1]
                        [shadow]
                            true
            {if}
                {Record/exists}
                    @channel
            .{then}
                {Thread/updateRtcSessions}
                    [0]
                        @channel
                    [1]
                        @res
                        .{Dict/get}
                            rtcSessions
`;
