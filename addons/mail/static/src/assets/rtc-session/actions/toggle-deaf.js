/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Toggles the deaf state of the current session, this must be a session
        of the current partner.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcSession/toggleDeaf
        [Action/params]
            record
                [type]
                    RtcSession
        [Action/behavior]
            {if}
                @record
                .{RtcSession/rtc}
                .{isFalsy}
            .{then}
                {break}
            {if}
                {Rtc/currentRtcSession}
                .{RtcSession/isDeaf}
            .{then}
                {Rtc/undeafen}
            .{else}
                {Rtc/deafen}
`;
