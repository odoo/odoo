/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mainParticipantCard
        [Element/model]
            RtcCallViewerComponent
        [Element/isPresent]
            @record
            .{RtcCallViewerComponent/rtcCallViewer}
            .{RtcCallViewer/mainParticipantCard}
        [Record/models]
            RtcCallViewerComponent/participantCard
        [web.Element/target]
            RtcCallParticipantCardComponent
        [RtcCallParticipantCardComponent/callParticipantCard]
            @record
            .{RtcCallViewerComponent/rtcCallViewer}
            .{RtcCallViewer/mainParticipantCard}
        [web.Element/class]
            w-100
`;
