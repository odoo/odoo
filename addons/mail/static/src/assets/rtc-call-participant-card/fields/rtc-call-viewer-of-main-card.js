/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The callViewer for which this card is the spotlight.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            rtcCallViewerOfMainCard
        [Field/model]
            RtcCallParticipantCard
        [Field/type]
            one
        [Field/target]
            RtcCallViewer
        [Field/inverse]
            RtcCallViewer/mainParticipandCard
`;
