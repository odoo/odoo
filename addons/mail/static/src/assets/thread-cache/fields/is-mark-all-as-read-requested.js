/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether this cache should consider calling "mark all as
        read" on this thread.

        This field is a hint that may or may not lead to an actual call.
        @see 'onChangeMarkAllAsRead'
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isMarkAllAsReadRequested
        [Field/model]
            ThreadCache
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
