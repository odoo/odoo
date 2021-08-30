/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            name
        [Element/model]
            RtcCallParticipantCardComponent
        [web.Element/tag]
            span
        [Element/isPresent]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/isMinimized}
            .{isFalsy}
        [web.Element/textContent]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/name}
        [web.Element/style]
            [web.scss/padding]
                {scss/map-get}
                    {scss/$spacers}
                    1
            {web.scss/include}
                {web.scss/text-truncate}
            [web.scss/color]
                white
            [web.scss/background-color]
                {scss/rgba}
                    black
                    0.8
            [web.scss/border-radius]
                {scss/$o-mail-rounded-rectangle-border-radius-sm}
`;
