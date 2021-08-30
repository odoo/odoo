/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            gridTile
        [Context/model]
            RtcCallViewerComponent
        [Model/fields]
            participantCard
        [Model/template]
            gridTileForeach
                gridTile
`;
