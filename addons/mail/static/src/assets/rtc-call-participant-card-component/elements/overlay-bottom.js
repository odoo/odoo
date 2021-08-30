/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            overlayBottom
        [Element/model]
            RtcCallParticipantCardComponent
        [web.Element/tag]
            span
        [Element/isPresent]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/rtcSession}
        [web.Element/style]
            [web.scss/position]
                absolute
            [web.scss/display]
                flex
            [web.scss/pointer-events]
                none
            [web.scss/margin]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/max-width]
                50%
            [web.scss/overflow]
                hidden
            [web.scss/bottom]
                0
            [web.scss/left]
                0
`;
