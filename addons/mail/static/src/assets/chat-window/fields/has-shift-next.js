/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasShiftNext
        [Field/model]
            ChatWindow
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            {if}
                @record
                .{ChatWindow/manager}
            .{then}
                false
                {break}
            {if}
                @record
                .{ChatWindow/manager}
                .{ChatWindowManager/allOrderedVisible}
                .{Collection/includes}
                    @record
                .{isFalsy}
            .{then}
                false
            .{else}
                @record
                .{ChatWindow/manager}
                .{ChatWindowManager/allOrderedVisible}
                .{Collection/indexOf}
                    @record
                .{>}
                    0
`;
