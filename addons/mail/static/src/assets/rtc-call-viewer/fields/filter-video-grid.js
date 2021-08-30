/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether we only display the videos or all the participants
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            filterVideoGrid
        [Field/model]
            RtcCallViewer
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
