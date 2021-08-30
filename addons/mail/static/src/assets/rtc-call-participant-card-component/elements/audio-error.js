/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            audioError
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
                .{RtcSession/isAudioInError}
        [web.Element/title]
            {Locale/text}
                Issue with audio
        [web.Element/class]
            text-danger
`;
