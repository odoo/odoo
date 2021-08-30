/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            lastVisible
        [Field/model]
            ChatWindowManager
        [Field/type]
            one
        [Field/target]
            ChatWindow
        [Field/compute]
            {if}
                @record
                .{ChatWindowManager/allOrderedVisible}
                .{Collection/last}
                .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                @record
                .{ChatWindowManager/allOrderedVisible}
                .{Collection/last}
`;
