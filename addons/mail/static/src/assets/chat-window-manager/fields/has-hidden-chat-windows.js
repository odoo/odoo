/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasHiddenChatWindows
        [Field/model]
            ChatWindowManager
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{ChatWindowManager/allOrderedHidden}
            .{Collection/length}
            .{>}
                0
`;
