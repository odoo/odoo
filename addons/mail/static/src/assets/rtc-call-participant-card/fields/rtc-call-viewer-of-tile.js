/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The callViewer for which this card is one of the tiles.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcCallViewerOfTile
        [Field/model]
            RtcCallParticipantCard
        [Field/type]
            one
        [Field/target]
            RtcCallViewer
        [Field/inverse]
            RtcCallViewer/tileParticipantCards
`;
