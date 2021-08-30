/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            liveIndicatorTop
        [Element/model]
            RtcCallParticipantCardComponent
        [Record/models]
            RtcCallParticipantCardComponent/liveIndicator
        [Element/isPresent]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/rtcSession}
            .{RtcSession/isScreenSharingOn}
            .{&}
                @record
                .{RtcCallParticipantCardComponent/callParticipantCard}
                .{RtcCallParticipantCard/isMinimized}
                .{isFalsy}
            .{&}
                @record
                .{RtcCallParticipantCardComponent/callParticipantCard}
                .{RtcCallParticipantCard/rtcSession}
                .{RtcSession/channel}
                .{Thread/rtc}
                .{isFalsy}
`;
