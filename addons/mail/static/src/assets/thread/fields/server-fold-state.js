/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine the last fold state known by the server, which is the fold
        state displayed after initialization or when the last pending
        fold state change was confirmed by the server.

        This field should be considered read only in most situations. Only
        the code handling fold state change from the server should typically
        update it.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            serverFoldState
        [Field/model]
            Thread]
        [Field/type]
            attr
        [Field/target]
            String
        [Field/default]
            closed
`;
