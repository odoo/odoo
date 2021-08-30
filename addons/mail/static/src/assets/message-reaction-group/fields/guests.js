/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the guests that have used this reaction on this message.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            guests
        [Field/model]
            MessageReactionGroup
        [Field/type]
            many
        [Field/target]
            Guest
`;
