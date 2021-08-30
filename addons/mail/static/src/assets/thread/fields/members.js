/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            members
        [Field/model]
            Thread
        [Field/type]
            many
        [Field/target]
            Partner
        [Field/inverse]
            Partner/memberThreads
        [Field/sort]
            [defined-first]
                Thread/nameOrDisplayName
            [case-insensitive-asc]
                Thread/nameOrDisplayName
`;
