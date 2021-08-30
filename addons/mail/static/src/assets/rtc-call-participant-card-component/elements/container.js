/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            container
        [Element/model]
            RtcCallParticipantCardComponent
        [web.Element/title]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/name}
        [web.Element/aria-label]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/name}
        [Element/onClick]
            {RtcCallParticipantCard/onClick}
                [0]
                    @record
                    .{RtcCallParticipantCardComponent/callParticipantCard}
                [1]
                    @ev
        [web.Element/class]
            align-items-center
        [web.Element/style]
            [web.scss/margin]
                {scss/map-get}
                    {scss/$spacers}
                    0
            [web.scss/width]
                100%
                .{-}
                    {scss/map-get}
                        {scss/$spacers}
                        0
            [web.scss/height]
                100%
                .{-}
                    {scss/map-get}
                        {scss/$spacers}
                        0
            [web.scss/display]
                flex
            [web.scss/position]
                relative
            [web.scss/justify-content]
                center
            [web.scss/flex-direction]
                column
            [web.scss/border-radius]
                {scss/$o-mail-rounded-rectangle-border-radius-sm}
`;
