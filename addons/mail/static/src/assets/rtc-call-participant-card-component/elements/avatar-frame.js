/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            avatarFrame
        [Element/model]
            RtcCallParticipantCardComponent
        [Element/isPresent]
            @record
            .{RtcCallParticipantCardComponent/callParticipantCard}
            .{RtcCallParticipantCard/rtcSession}
            .{isFalsy}
            .{|}
                @record
                .{RtcCallParticipantCardComponent/callParticipantCard}
                .{RtcCallParticipantCard/rtcSession}
                .{RtcSession/videoStream}
                .{isFalsy}
        [web.Element/class]
            mh-100
            mw-100
            h-100
            align-items-center
            justify-content-center
        [web.Element/isDraggable]
            false
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/user-select]
                none
            [web.scss/aspect-ratio]
                16/9
            {if}
                @record
                .{RtcCallParticipantCardComponent/callParticipantCard}
                .{RtcCallParticipantCard/isMinimized}
            .{then}
                [web.scss/aspect-ratio]
                    1
            [web.scss/border-radius]
                {scss/$o-mail-rounded-rectangle-border-radius-sm}
            {if}
                @record
                .{RtcCallParticipantCardComponent/callParticipantCard}
                .{RtcCallParticipantCard/isMinimized}
                .{isFalsy}
            .{then}
                [web.scss/background-color]
                    {scss/$o-brand-secondary}
`;
