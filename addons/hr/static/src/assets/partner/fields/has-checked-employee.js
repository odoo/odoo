/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Whether an attempt was already made to fetch the employee corresponding
        to this partner. This prevents doing the same RPC multiple times.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasCheckedEmployee
        [Field/model]
            Partner
        [Field/feature]
            hr
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
