/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine if there is a pending seen message change, which is a change
        of seen message requested by the client but not yet confirmed by the
        server.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            pendingSeenMessageId
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Number
`;
