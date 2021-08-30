/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            connectionState
        [Element/model]
            RtcCallParticipantCardComponent
        [Record/models]
            RtcCallParticipantCardComponent/overlayTopElement
        [Element/isPresent]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/rtcSession}
            .{RtcSession/channel}
            .{Thread/rtc}
            .{&}
                @record
                .{RtcCallParticipantCardComponent/callParticipantCard}
                .{RtcCallParticipantCard/rtcSession}
                .{RtcSession/rtc}
                .{isFalsy}
            .{&}
                {Record/insert}
                    [Record/models]
                        Collection
                    connected
                    completed
                .{Collection/includes}
                    @record
                    .{RtcCallParticipantCardComponent/callParticipantCard}
                    .{RtcCallParticipantCard/rtcSession}
                    .{RtcSession/connectionState}
                .{isFalsy}
        [web.Element/title]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/rtcSession}
            .{RtcSession/connectionState}
        [web.Element/aria-label]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/rtcSession}
            .{RtcSession/connectionState}
`;
