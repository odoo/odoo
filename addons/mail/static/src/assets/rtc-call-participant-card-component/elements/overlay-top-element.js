/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            overlayTopElement
        [Element/model]
            RtcCallParticipantCardComponent
        [web.Element/tag]
            span
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/justify-content]
                center
            [web.scss/flex-direction]
                column
            [web.scss/margin-inline-end]
                5%
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    2
            {if}
                @record
                .{RtcCallParticipantCardComponent/callParticipantCard}
                .{RtcCallParticipantCard/isMinimized}
            .{then}
                [web.scss/padding]
                    {scss/map-get}
                        {scss/$spacers}
                        1
            [web.scss/color]
                white
            [web.scss/border-radius]
                50%
            [web.scss/background-color]
                {scss/gray}
                    900
`;
