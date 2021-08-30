/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            overlayTop
        [Element/model]
            RtcCallParticipantCardComponent
        [Element/isPresent]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/rtcSession}
        [web.Element/style]
            [web.scss/position]
                absolute
            [web.scss/display]
                flex
            [web.scss/flex-direction]
                row-reverse
            [web.scss/margin]
                {scss/map-get}
                    {scss/$spacers}
                    2
            [web.scss/right]
                0%
            [web.scss/top]
                0%
`;
