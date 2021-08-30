/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcCallParticipantCard/onChangeVolume
        [Action/params]
            ev
                [type]
                    web.Event
            record
                [type]
                    RtcCallParticipantCard
        [Action/behavior]
            {if}
                @record
                .{RtcCallParticipantCard/rtcSession}
            .{then}
                {RtcSession/setVolume}
                    [0]
                        @record
                        .{RtcCallParticipantCard/rtcSession}
                    [1]
                        @ev
                        .{web.Event/target}
                        .{web.Element/value}
`;
