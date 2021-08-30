/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            guestMembers
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Partner
        [Field/sort]
            [defined-first]
                Thread/name
            [case-insensitive-asc]
                Thread/name
`;
