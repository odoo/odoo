/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
{Dev/comment}
        States the number of members in this thread according to the server.
        Guests are excluded from the count.
        Only makes sense if this thread is a channel.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            memberCount
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Integer
`;
