/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            volumeMenuAnchorPopoverInput
        [Element/model]
            RtcCallParticipantCardComponent
        [web.Element/tag]
            input
        [web.Element/type]
            range
        [web.Element/min]
            0.0
        [web.Element/step]
            0.01
        [web.Element/value]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/rtcSession}
            .{RtcSession/volume}
        [Element/onChange]
            {RtcCallParticipantCard/onChangeVolume}
                [0]
                    @record
                    .{RtcCallParticipantCardComponent/callParticipantCard}
                [1]
                    @ev
`;
