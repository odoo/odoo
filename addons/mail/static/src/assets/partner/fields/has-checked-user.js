/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Whether an attempt was already made to fetch the user corresponding
        to this partner. This prevents doing the same RPC multiple times.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasCheckedUser
        [Field/model]
            Partner
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
