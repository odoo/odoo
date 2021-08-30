/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Boolean that determines whether this thread is pinned
        in discuss and present in the messaging menu.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isPinned
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{Thread/isPendingPinned}
            .{??}
                @record
                .{Thread/isServerPinned}
`;
