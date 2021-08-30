/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Client-side ending of the call.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/endCall
        [Action/params]
            record
                [type]
                    Thread
        [Action/behavior]
            {if}
                @record
                .{Thread/rtc}
            .{then}
                {Rtc/reset}
                    @record
                    .{Thread/rtc}
                {SoundEffects/channelLeave}
                .{SoundEffect/play}
            {Record/update}
                [0]
                    @record
                [1]
                    [Thread/rtc]
                        {Record/empty}
                    [Thread/rtcInvitingSession]
                        {Record/empty}
`;
