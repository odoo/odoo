/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine if there is a pending pin state change, which is a change
        of pin state requested by the client but not yet confirmed by the
        server.

        This field can be updated to immediately change the pin state on the
        interface and to notify the server of the new state.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isPendingPinned
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
