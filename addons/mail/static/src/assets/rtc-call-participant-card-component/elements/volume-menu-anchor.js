/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            volumeMenuAnchor
        [Element/model]
            RtcCallParticipantCardComponent
        [Element/isPresent]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/rtcSession}
            .{RtcSession/isOwnSession}
            .{isFalsy}
        [web.Element/tag]
            i
        [Element/onClick]
            {RtcCallParticipantCard/onClickVolumeAnchor}
                [0]
                    @record
                    .{RtcCallParticipantCardComponent/callParticipantCard}
                [1]
                    @ev
`;
