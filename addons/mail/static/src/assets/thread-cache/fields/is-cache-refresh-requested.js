/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether 'this' should consider refreshing its messages.
        This field is a hint that may or may not lead to an actual refresh.
        @see 'hasToLoadMessages'
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isCacheRefreshRequested
        [Field/model]
            ThreadCache
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
