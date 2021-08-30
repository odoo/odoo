/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine the last pin state known by the server, which is the pin
        state displayed after initialization or when the last pending
        pin state change was confirmed by the server.

        This field should be considered read only in most situations. Only
        the code handling pin state change from the server should typically
        update it.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isServerPinned
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
