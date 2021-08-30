/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            participantCard
        [Field/model]
            RtcCallViewerComponent:gridTile
        [Field/type]
            one
        [Field/target]
            RtcCallParticipandCard
        [Field/isRequired]
            true
`;
