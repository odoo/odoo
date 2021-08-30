/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            rtcVideo
        [Element/model]
            RtcCallParticipantCardComponent
        [Element/isPresent]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/rtcSession}
            .{&}
                @record
                .{RtcCallParticipantCardComponent/callParticipantCard}
                .{RtcCallParticipantCard/rtcSession}
                .{RtcSession/videoStream}
        [Field/target]
            RtcVideoComponent
        [RtcVideoComponent/rtcSession]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/rtcSession}
        [Element/onClick]
            {RtcCallParticipantCard/onClickVideo}
                [0]
                    @record
                    .{RtcCallParticipantCardComponent/callParticipantCard}
                [1]
                    @ev
`;
