/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if this card has to be displayed in a minimized form.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isMinimized
        [Field/model]
            RtcCallParticipantCard
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            False
        [Field/compute]
            :callViewer
                @record
                .{RtcCallParticipantCard/rtcCallViewerOfMainCard}
                .{|}
                    @record
                    .{RtcCallParticipantCard/rtcCallViewerOfTile}
            @callViewer
            .{&}
                @callViewer
                .{RtcCallViewer/isMinimized}
`;
