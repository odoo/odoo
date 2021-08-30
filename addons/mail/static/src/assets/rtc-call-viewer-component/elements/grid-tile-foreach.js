/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            gridTileForeach
        [Element/model]
            RtcCallViewerComponent
        [Record/models]
            Foreach
        [Foreach/collection]
            @record
            .{RtcCallViewerComponent/rtcCallViewer}
            .{RtcCallViewer/tileParticipantCards}
        [Foreach/as]
            participantCard
        [Element/key]
            grid_tile_
            .{+}
                @field
                .{Foreach/get}
                    participantCard
                .{Record/id}
        [Field/target]
            RtcCallViewerComponent:gridTile
        [RtcCallViewerComponent:gridTile/participantCard]
            @field
            .{Foreach/get}
                participandCard
`;
