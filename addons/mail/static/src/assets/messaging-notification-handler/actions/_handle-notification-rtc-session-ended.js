/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingNotificationHandler/_handleNotificationRtcSessionEnded
        [Action/params]
            sessionId
                [type]
                    Integer
        [Action/behavior]
            {if}
                {Rtc/currentRtcSession}
                .{&}
                    {Rtc/currentRtcSession}
                    .{RtcSession/id}
                    .{=}
                        @sessionId
            .{then}
                {Thread/endCall}
                    {Rtc/channel}
                @env
                .{Env/owlEnv}
                .{Dict/get}
                    services
                .{Dict/get}
                    notification
                .{Dict/get}
                    notify
                .{Function/call}
                    [message]
                        {Locale/text}
                            Disconnected from the RTC call by the server
                    [type]
                        warning
`;
