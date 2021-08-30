/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcController/onClickDeafen
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    RtcController
        [Action/behavior]
            {if}
                {Rtc/currentRtcSession}
                .{RtcSession/isDeaf}
            .{then}
                {Rtc/undeafen}
            .{else}
                {Rtc/deafen}
`;
